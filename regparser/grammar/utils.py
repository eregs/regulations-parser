from collections import namedtuple
import re

import pyparsing


def keep_pos(source, location, tokens):
    """Wrap the tokens with a class that also keeps track of the match's
    location."""
    return (WrappedResult(tokens, location, pyparsing.getTokensEndLoc()),)


Position = namedtuple('Position', ['start', 'end'])


class WrappedResult():
    """Keep track of matches along with their position. This is a bit of a
    hack to get around PyParsing's tendency to drop that info."""
    def __init__(self, tokens, start, end):
        self.tokens = tokens
        self.pos = Position(start, end)

    def __getattr__(self, attr):
        return getattr(self.tokens, attr)


class DocLiteral(pyparsing.Literal):
    """Setting an objects name to a unicode string causes Sphinx to freak
    out. Instead, we'll replace with the provided (ascii) text."""
    def __init__(self, literal, ascii_text):
        super(DocLiteral, self).__init__(literal)
        self.name = ascii_text


def WordBoundaries(grammar):
    return (pyparsing.WordStart(pyparsing.alphanums) +
            grammar +
            pyparsing.WordEnd(pyparsing.alphanums))


def Marker(txt):
    return pyparsing.Suppress(WordBoundaries(pyparsing.CaselessLiteral(txt)))


def SuffixMarker(txt):
    return pyparsing.Suppress(pyparsing.CaselessLiteral(txt) +
                              pyparsing.WordEnd(pyparsing.alphanums))


class QuickSearchable(pyparsing.ParseElementEnhance):
    """Pyparsing's `scanString` (i.e. searching for a grammar over a string)
    tests each index within its search string. While that offers maximum
    flexibility, it is rather slow for our needs. This enhanced grammar type
    wraps other grammars, deriving from them a first regular expression to use
    when `scanString`ing. This cuts search time considerably."""
    def __init__(self, expr):
        super(QuickSearchable, self).__init__(expr)
        regex_strs = []
        for regex_str in QuickSearchable.initial_regex(expr):
            if '|' in regex_str:
                # If the regex includes an "or", we need to wrap it in parens
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

    def scanString(self, instring, maxMatches=None, overlap=False):
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
                except pyparsing.ParseException:
                    search_idx = match.start() + 1
            else:
                search_idx = len(instring)

    @staticmethod
    def initial_regex(grammar):
        """Given a Pyparsing grammar, derive a set of suitable initial regular
        expressions to aid our search. As grammars may `Or` together multiple
        sub-expressions, this always returns a `set` of possible regular
        expression strings. This is _not_ a complete conversion to regexes nor
        does it account for every Pyparsing element; add as needed"""
        recurse = QuickSearchable.initial_regex
        # Optimization: WordStart is generally followed by a more specific
        # identifier. Rather than searching for the start of a word alone,
        # search for that identifier as well
        if (isinstance(grammar, pyparsing.And) and
                isinstance(grammar.exprs[0], pyparsing.WordStart)):
            boundry, next_expr = grammar.exprs[:2]
            word_chars = ''.join(re.escape(char)
                                 for char in boundry.wordChars)
            return set('(?<![{}])'.format(word_chars) + regex_str
                       for regex_str in recurse(next_expr))
        if (isinstance(grammar, pyparsing.And) and
                isinstance(grammar.exprs[0], pyparsing.Optional)):
            return recurse(grammar.exprs[0].expr) | recurse(grammar.exprs[1])
        elif isinstance(grammar, pyparsing.And):
            return recurse(grammar.exprs[0])
        elif isinstance(grammar, (pyparsing.MatchFirst, pyparsing.Or)):
            return reduce(lambda so_far, expr: so_far | recurse(expr),
                          grammar.exprs, set())
        elif isinstance(grammar, (pyparsing.Suppress, QuickSearchable)):
            return recurse(grammar.expr)
        elif isinstance(grammar, (pyparsing.Regex, pyparsing.Word)):
            return set([grammar.reString])
        elif isinstance(grammar, pyparsing.LineStart):
            return set(['^'])
        elif isinstance(grammar, pyparsing.Literal):
            return set([re.escape(grammar.match)])
        # Grammar type that we've not accounted for. Fail fast
        else:
            raise Exception("Unknown grammar type: {}".format(
                grammar.__class__))
