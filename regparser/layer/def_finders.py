# -*- coding: utf-8 -*-
"""Parsers for finding a term that's being defined within a node"""
import abc
import re
from collections import namedtuple
from itertools import chain

import six
from pyparsing import ParseException

from regparser.citations import Label
from regparser.grammar import terms as grammar
from regparser.tree.struct import Node
from regparser.web.settings import parser as settings


class Ref(namedtuple('Ref', ['term', 'label', 'start'])):
    """A reference to a defined term. Keeps track of the term, where it was
    found and the term's position in that node's text"""
    def __new__(cls, term, label, start):
        term = six.text_type(term).lower()
        return super(Ref, cls).__new__(cls, term, label, start)

    @property
    def end(self):
        return self.start + len(self.term)

    @property
    def position(self):
        return (self.start, self.end)


class FinderBase(six.with_metaclass(abc.ABCMeta)):
    """Base class for all of the definition finder classes. Defines the
    interface they must implement"""
    @abc.abstractmethod
    def find(self, node):
        """Given a Node, pull out any definitions it may contain as a list of
        Refs"""
        raise NotImplementedError()


class ExplicitIncludes(FinderBase):
    """Definitions can be explicitly included in the settings. For example,
    say that a paragraph doesn't indicate that a certain phrase is a
    definition; we can define INCLUDE_DEFINITIONS_IN in our settings file,
    which will be checked here."""
    def find(self, node):
        refs = []
        cfr_part = node.label[0] if node.label else None
        included = list(settings.INCLUDE_DEFINITIONS_IN.get("ALL", []))  # copy
        included.extend(settings.INCLUDE_DEFINITIONS_IN.get(cfr_part, []))
        for included_term, context in included:
            if context in node.text and included_term in node.text:
                pos_start = node.text.index(included_term)
                refs.append(Ref(included_term, node.label_id(), pos_start))
        return refs


class SmartQuotes(FinderBase):
    """Definitions indicated via smart quotes"""
    def __init__(self, stack):
        """Stack (which references ancestors of a node) is used to determine
        whether or not to apply smart quotes"""
        self.stack = stack

    def find(self, node):
        refs = []
        if self.stack and self.has_def_indicator():
            for match, _, _ in grammar.smart_quotes.scanString(node.text):
                term = match.term[0].strip(',.;')
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


class ScopeMatch(FinderBase):
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
            valid_term = re.match("^[a-z ]+$", match.term[0])
            if valid_scope and valid_term:
                term = match.term[0].strip()
                pos_start = node.text.index(term, match.term.pos[0])
                refs.append(Ref(term, node.label_id(), pos_start))
        return refs


class XMLTermMeans(FinderBase):
    """Namespace for a matcher for e.g. '<E>XXX</E> means YYY'"""
    def __init__(self, existing_refs=None):
        """Existing refs will be used to exclude certain matches"""
        if existing_refs is None:
            existing_refs = []
        self.exclusions = list(existing_refs)

    def find(self, node):
        refs = []
        tagged_text = node.tagged_text
        for match, _, _ in grammar.xml_term_parser.scanString(tagged_text):
            # Position in match reflects XML tags, so its dropped in
            # preference of new values based on node.text.
            for match in chain([match.head], match.tail):
                pos_start = self.pos_start(match.term[0], node.text)
                term = node.tagged_text[match.term.pos[0]:match.term.pos[1]]
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


class DefinitionKeyterm(object):
    """Matches definitions identified by being a first-level paragraph in a
    section with a specific title"""
    _NORMALIZE_RE = re.compile(r'[^a-z]+')
    _section_titles = ['definition', 'meaningofterms']  # already normalized

    def __init__(self, parent):
        is_regtext = parent and parent.node_type == Node.REGTEXT
        is_section = is_regtext and len(parent.label) == 2
        title = parent and self._normalize(parent.title)
        title_match = title in self._section_titles
        self.title_matches = is_section and title_match

    @classmethod
    def _normalize(cls, title):
        """Makes a title comparable with cls._section_titles"""
        return cls._NORMALIZE_RE.sub('', (title or "").lower())

    @staticmethod
    def _split_phrase(phrase):
        """A single phrase might contain multiple terms. Attempt to split it
        into subphrases. Using a heuristic, we declare that if all subphrases
        are a single word long, those subphrases are each terms. In this way,
        we treat "apple or banana or pear" as three different terms, but see
        only one term in "fruit salad or mix" (the whole phrase)"""
        potential_terms = phrase.split(" or ")
        if any(" " in term for term in potential_terms):
            return [phrase]
        else:
            return potential_terms

    def find(self, node):
        if self.title_matches:
            tagged_text = node.tagged_text
            try:
                match = grammar.key_term_parser.parseString(tagged_text)
                phrase = node.tagged_text[match.term.pos[0]:match.term.pos[1]]
                return [Ref(term, node.label_id(), node.text.find(term))
                        for term in self._split_phrase(phrase)]
            except ParseException:
                return []
        return []
