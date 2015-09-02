# vim: set fileencoding=utf-8
"""Parsers for finding a term that's being defined within a node"""
from itertools import chain
import re

from regparser.citations import Label
from regparser.grammar import terms as grammar
import settings


class Ref(object):
    def __init__(self, term, label, start):
        self.term = unicode(term)
        self.label = label
        self.start = start
        self.end = self.start + len(term)
        self.position = (self.start, self.end)

    def __eq__(self, other):
        """Equality depends on equality of the fields"""
        return isinstance(other, Ref) and repr(self) == repr(other)

    def __repr__(self):
        return 'Ref( term=%s, label=%s, start=%s )' % (
            repr(self.term), repr(self.label), repr(self.start))


class ExplicitIncludes(object):
    """Definitions can be explicitly included in the settings"""
    def find(self, node):
        refs = []
        cfr_part = node.label[0] if node.label else None
        for included_term, context in settings.INCLUDE_DEFINITIONS_IN.get(
                cfr_part, []):
            if context in node.text and included_term in node.text:
                pos_start = node.text.index(included_term)
                term = included_term.lower()
                refs.append(Ref(term, node.label_id(), pos_start))
        return refs


class SmartQuotes(object):
    """Definitions indicated via smart quotes"""
    def __init__(self, stack):
        """Stack (which references ancestors of a node) is used to determine
        whether or not to apply smart quotes"""
        self.stack = stack

    def find(self, node):
        refs = []
        if self.stack and self.has_def_indicator():
            for match, _, _ in grammar.smart_quotes.scanString(node.text):
                term = match.term.tokens[0].lower().strip(',.;')
                refs.append(Ref(term, node.label_id(), match.term.pos[0]))
        return refs

    def has_def_indicator(self):
        """With smart quotes, we catch some false positives, phrases in quotes
        that are not terms. This extra test lets us know that a parent of the
        node looks like it would contain definitions."""
        for node in self.stack.lineage():
            lower_text = node.text.lower()
            in_text = 'Definition' in node.text
            in_title = 'Definition' in (node.title or '')
            pattern1 = re.search('the term .* (means|refers to)', lower_text)
            pattern2 = re.search(u'“[^”]+” (means|refers to)', lower_text)
            if in_text or in_title or pattern1 or pattern2:
                return True
        return False


class ScopeMatch(object):
    """We know these will be definitions because the scope of the definition
    is spelled out. E.g. 'for the purposes of XXX, the term YYY means'"""
    def __init__(self, finder):
        """Finder is an instance of ScopeFinder"""
        self.finder = finder

    def find(self, node):
        refs = []
        for match, _, _ in grammar.scope_term_type_parser.scanString(
                node.text):
            valid_scope = self.finder.scope_of_text(
                match.scope, Label.from_node(node), verify_prefix=False)
            valid_term = re.match("^[a-z ]+$", match.term.tokens[0])
            if valid_scope and valid_term:
                term = match.term.tokens[0].strip()
                pos_start = node.text.index(term, match.term.pos[0])
                refs.append(Ref(term, node.label_id(), pos_start))
        return refs


class XMLTermMeans(object):
    """Namespace for a matcher for e.g. '<E>XXX</E> means YYY'"""
    def __init__(self, existing_refs):
        """Existing refs will be used to exclude certain matches"""
        self.exclusions = list(existing_refs)

    def find(self, node):
        refs = []
        tagged_text = getattr(node, 'tagged_text', '')
        for match, _, _ in grammar.xml_term_parser.scanString(tagged_text):
            """Position in match reflects XML tags, so its dropped in
            preference of new values based on node.text."""
            for match in chain([match.head], match.tail):
                pos_start = self.pos_start(match.term.tokens[0], node.text)
                term = node.tagged_text[
                    match.term.pos[0]:match.term.pos[1]].lower()
                ref = Ref(term, node.label_id(), pos_start)
                refs.append(ref)
                self.exclusions.append(ref)
        return refs

    def pos_start(self, needle, haystack):
        """Search for the first instance of `needle` in the `haystack`
        excluding any overlaps from `self.exclusions`. Implicitly returns None
        if it can't be found"""
        start = 0
        while start >= 0:
            start = haystack.find(needle, start)
            if not any(r.start <= start and r.end >= start
                       for r in self.exclusions):
                return start
            start += 1
