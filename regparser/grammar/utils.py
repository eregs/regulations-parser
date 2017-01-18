import re
from collections import namedtuple

import pyparsing as pp
from six.moves import reduce

Position = namedtuple('Position', ['start', 'end'])


def keep_pos(expr):
    """Transform a pyparsing grammar by inserting an attribute, "pos", on the
    match which describes position information"""
    loc_marker = pp.Empty().setParseAction(lambda s, loc, t: loc)
    end_loc_marker = loc_marker.copy()
    end_loc_marker.callPreparse = False   # don't allow the cursor to move
    return (
        loc_marker.setResultsName("pos_start") +
        expr +
        end_loc_marker.setResultsName("pos_end")
    ).setParseAction(parse_position)


def parse_position(source, location, tokens):
    """A pyparsing parse action which pulls out (and removes) the position
    information and replaces it with a Position object"""
    start, end = tokens['pos_start'], tokens['pos_end']
    del tokens[0]
    del tokens[-1]
    del tokens['pos_start']
    del tokens['pos_end']
    tokens['pos'] = Position(start, end)
    return tokens


class DocLiteral(pp.Literal):
    """Setting an objects name to a unicode string causes Sphinx to freak
    out. Instead, we'll replace with the provided (ascii) text."""
    def __init__(self, literal, ascii_text):
        super(DocLiteral, self).__init__(literal)
        self.name = ascii_text


def WordBoundaries(grammar):    # noqa - we treat this like a pyparsing class
    return (pp.WordStart(pp.alphanums) +
            grammar +
            pp.WordEnd(pp.alphanums))


def Marker(txt):    # noqa - we treat this like a pyparsing class
    return pp.Suppress(WordBoundaries(pp.CaselessLiteral(txt)))


def SuffixMarker(txt):  # noqa - we treat this like a pyparsing class
    return pp.Suppress(pp.CaselessLiteral(txt) + pp.WordEnd(pp.alphanums))


class QuickSearchable(pp.ParseElementEnhance):
    """Pyparsing's `scanString` (i.e. searching for a grammar over a string)
    tests each index within its search string. While that offers maximum
    flexibility, it is rather slow for our needs. This enhanced grammar type
    wraps other grammars, deriving from them a first regular expression to use
    when `scanString`ing. This cuts search time considerably."""
    cases = []

    def __init__(self, expr, force_regex_str=None):
        super(QuickSearchable, self).__init__(expr)
        regex_strs = []
        if force_regex_str is not None:
            regex_strs.append(force_regex_str)
        else:
            for regex_str in QuickSearchable.initial_regex(expr):
                if '|' in regex_str:
                    # If the regex includes an "or", we need to wrap it in
                    # parens
                    regex_str = '(' + regex_str + ')'
                regex_strs.append(regex_str)
            # Combine all potential initial_regexes with an "or". Match
            # Pyparsing's naming convention
        self.reString = '|'.join(regex_strs)
        self.re = re.compile(
            self.reString,
            # Be as forgiving as possible with flags; false negatives aren't
            # acceptable but false positives are fine
            re.IGNORECASE | re.UNICODE | re.MULTILINE | re.DOTALL)
        self.parseImpl = expr.parseImpl

    def scanString(self, instring, maxMatches=None, overlap=False):     # noqa
        """Override `scanString` to attempt parsing only where there's a regex
        search match (as opposed to every index). Does not implement the full
        scanString interface."""
        if maxMatches is not None or overlap:
            raise ValueError("QuickScannable does not implement the full "
                             "scanString interface")
        search_idx = 0
        while search_idx < len(instring):
            match = self.re.search(instring, search_idx)
            if match:
                try:
                    pre_loc = self.expr.preParse(instring, match.start())
                    next_loc, tokens = self.expr._parse(
                        instring, match.start(), callPreParse=False)
                    if next_loc > match.start():
                        yield tokens, pre_loc, next_loc
                        search_idx = next_loc
                    else:
                        search_idx += 1
                except pp.ParseException:
                    search_idx = match.start() + 1
            else:
                search_idx = len(instring)

    @classmethod
    def initial_regex(cls, grammar):
        """Given a Pyparsing grammar, derive a set of suitable initial regular
        expressions to aid our search. As grammars may `Or` together multiple
        sub-expressions, this always returns a `set` of possible regular
        expression strings. This is _not_ a complete conversion to regexes nor
        does it account for every Pyparsing element; add as needed"""
        for case in cls.cases:
            if case.matches(grammar):
                return case(grammar)
        # Grammar type that we've not accounted for. Fail fast
        raise Exception("Unknown grammar type: {0}".format(grammar.__class__))

    @classmethod
    def case(cls, *match_classes):
        """Add a "case" which will match grammars based on the provided
        class types. If there's a match, we'll execute the function"""
        def inner(process_fn):
            process_fn.matches = lambda g: isinstance(g, match_classes)
            cls.cases.append(process_fn)
            return process_fn
        return inner

    @classmethod
    def and_case(cls, *first_classes):
        """"And" grammars are relatively common; while we generally just want
        to look at their first terms, this decorator lets us describe special
        cases based on the class type of the first component of the clause"""
        def inner(process_fn):
            process_fn.matches = (lambda g: isinstance(g, pp.And)
                                  and isinstance(g.exprs[0], first_classes))
            cls.cases.append(process_fn)
            return process_fn
        return inner


@QuickSearchable.and_case(pp.WordStart)
def wordstart(grammar):
    """Optimization: WordStart is generally followed by a more specific
    identifier. Rather than searching for the start of a word alone, search
    for that identifier as well"""
    boundry, next_expr = grammar.exprs[:2]
    word_chars = ''.join(re.escape(char)
                         for char in boundry.wordChars)
    return {'(?<![{0}])'.format(word_chars) + regex_str
            for regex_str in QuickSearchable.initial_regex(next_expr)}


@QuickSearchable.and_case(pp.Optional)
def optional(grammar):
    with_grammar = QuickSearchable.initial_regex(grammar.exprs[0].expr)
    without_grammar = QuickSearchable.initial_regex(grammar.exprs[1])
    return with_grammar | without_grammar


@QuickSearchable.and_case(pp.Empty)
def empty(grammar):
    return QuickSearchable.initial_regex(grammar.exprs[1])


@QuickSearchable.case(pp.And)
def match_and(grammar):
    return QuickSearchable.initial_regex(grammar.exprs[0])


@QuickSearchable.case(pp.MatchFirst, pp.Or)
def match_or(grammar):
    return reduce(
        lambda so_far, expr: so_far | QuickSearchable.initial_regex(expr),
        grammar.exprs, set()
    )


@QuickSearchable.case(pp.Suppress)
def suppress(grammar):
    return QuickSearchable.initial_regex(grammar.expr)


@QuickSearchable.case(pp.Regex, pp.Word, QuickSearchable)
def has_re_string(grammar):
    return {grammar.reString}


@QuickSearchable.case(pp.LineStart)
def line_start(grammar):
    return {'^'}


@QuickSearchable.case(pp.Literal)
def literal(grammar):
    return {re.escape(grammar.match)}
