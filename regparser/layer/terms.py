# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from collections import defaultdict, namedtuple

import inflection

from regparser.layer import def_finders
from regparser.layer.layer import Layer
from regparser.layer.scope_finder import ScopeFinder
from regparser.tree import struct
from regparser.tree.priority_stack import PriorityStack
from regparser.web.settings import parser as settings

try:
    key = ('(?i)(p)erson$', '\\1eople')
    del inflection.PLURALS[inflection.PLURALS.index(key)]
except ValueError:
    pass


MAX_TERM_LENGTH = 100
Inflected = namedtuple('Inflected', ['singular', 'plural'])


class ParentStack(PriorityStack):
    """Used to keep track of the parents while processing nodes to find
    terms. This is needed as the definition may need to find its scope in
    parents."""
    def unwind(self):
        """No collapsing needs to happen."""
        self.pop()

    def parent_of(self, node):
        level = self.peek_level(node.depth() - 1)
        return level[-1] if level else None


class Terms(Layer):
    shorthand = 'terms'
    STARTS_WITH_WORDCHAR = re.compile(r'^\w.*$')
    ENDS_WITH_WORDCHAR = re.compile(r'^.*\w$')

    def __init__(self, *args, **kwargs):
        Layer.__init__(self, *args, **kwargs)
        self.layer['referenced'] = {}
        #   scope -> List[(term, definition_ref)]
        self.scoped_terms = defaultdict(list)
        self.scope_finder = ScopeFinder()
        self._inflected = {}

    def inflected(self, term):
        """Check the memoized Inflected version of the provided term"""
        if term not in self._inflected:
            self._inflected[term] = Inflected(
                inflection.singularize(term), inflection.pluralize(term))
        return self._inflected[term]

    def look_for_defs(self, node, stack=None):
        """Check a node and recursively check its children for terms which are
        being defined. Add these definitions to self.scoped_terms."""
        stack = stack or ParentStack()
        stack.add(node.depth(), node)
        if node.node_type in (struct.Node.REGTEXT, struct.Node.SUBPART,
                              struct.Node.EMPTYPART):
            included, excluded = self.node_definitions(node, stack)
            if included:
                for scope in self.scope_finder.determine_scope(stack):
                    self.scoped_terms[scope].extend(included)
            self.scoped_terms['EXCLUDED'].extend(excluded)

            for child in node.children:
                self.look_for_defs(child, stack)

    def pre_process(self):
        """Step through every node in the tree, finding definitions. Also keep
        track of which subpart we are in. Finally, document all defined terms.
        """
        self.scope_finder.add_subparts(self.tree)
        self.look_for_defs(self.tree)

        referenced = self.layer['referenced']
        for scope in self.scoped_terms:
            for ref in self.scoped_terms[scope]:
                key = ref.term + ":" + ref.label
                if (key not in referenced or  # New term
                        # Or this term is earlier in the paragraph
                        ref.start < referenced[key]['position'][0]):
                    referenced[key] = {
                        'term': ref.term,
                        'reference': ref.label,
                        'position': ref.position
                    }

    def applicable_terms(self, label):
        """Find all terms that might be applicable to nodes with this label.
        Note that we don't have to deal with subparts as subpart_scope simply
        applies the definition to all sections in a subpart"""
        applicable_terms = {}
        for segment_length in range(1, len(label) + 1):
            scope = tuple(label[:segment_length])
            for ref in self.scoped_terms.get(scope, []):
                applicable_terms[ref.term] = ref    # overwrites
        return applicable_terms

    def is_exclusion(self, term, node):
        """Some definitions are exceptions/exclusions of a previously
        defined term. At the moment, we do not want to include these as they
        would replace previous (correct) definitions. We also remove terms
        which are inside an instance of the IGNORE_DEFINITIONS_IN setting"""
        applicable_terms = self.applicable_terms(node.label)
        if term in applicable_terms:
            regex = 'the term .?' + re.escape(term) + '.? does not include'
            if re.search(regex, node.text.lower()):
                return True
            for start, end in self.ignored_offsets(node.label[0], node.text):
                if term in node.text[start:end]:
                    return True
        return False

    def node_definitions(self, node, stack=None):
        """Find defined terms in this node's text."""
        references = []
        stack = stack or ParentStack()
        for finder in (def_finders.ExplicitIncludes(),
                       def_finders.SmartQuotes(stack),
                       def_finders.ScopeMatch(self.scope_finder),
                       def_finders.XMLTermMeans(references),
                       def_finders.DefinitionKeyterm(stack.parent_of(node))):
            # Note that `extend` is very important as XMLTermMeans uses the
            # list reference
            references.extend(finder.find(node))

        references = [r for r in references if len(r.term) <= MAX_TERM_LENGTH]

        return (
            [r for r in references if not self.is_exclusion(r.term, node)],
            [r for r in references if self.is_exclusion(r.term, node)])

    def process(self, node):
        """Determine which (if any) definitions would apply to this node,
        then find if any of those terms appear in this node"""
        applicable_terms = self.applicable_terms(node.label)

        layer_el = []
        #   Remove any definitions defined in this paragraph
        term_list = [
            (term, ref) for term, ref in applicable_terms.items()
            if ref.label != node.label_id()]

        exclusions = self.excluded_offsets(node)

        matches = self.calculate_offsets(node.text, term_list, exclusions)
        matches = sorted(matches, key=lambda triplet: triplet[0])
        for _, ref, offsets in matches:
            layer_el.append({
                "ref": ref.term + ':' + ref.label,
                "offsets": offsets
            })
        return layer_el

    def _word_matches(self, term, text):
        """Return the start and end indexes of the term within the text,
        accounting for word boundaries"""
        # @todo - this is rather slow -- probably want to memoize the results
        regex = re.escape(term)
        if self.STARTS_WITH_WORDCHAR.match(term):
            regex = r'\b' + regex
        if self.ENDS_WITH_WORDCHAR.match(term):
            regex += r'\b'
        regex = re.compile(regex)
        return [(match.start(), match.end())
                for match in regex.finditer(text)]

    def ignored_offsets(self, cfr_part, text):
        """Return a list of offsets corresponding to the presence of an
        "ignored" phrase in the text"""
        ignored_phrases = (settings.IGNORE_DEFINITIONS_IN.get('ALL', []) +
                           settings.IGNORE_DEFINITIONS_IN.get(cfr_part, []))
        positions = []
        for phrase in ignored_phrases:
            positions.extend(self._word_matches(phrase, text))
        return positions

    def excluded_offsets(self, node):
        """We explicitly exclude certain chunks of text (for example, words
        we are defining shouldn't have links appear within the defined
        term.) More will be added in the future"""
        exclusions = []
        for reflist in self.scoped_terms.values():
            exclusions.extend(
                ref.position for ref in reflist
                if ref.label == node.label_id())
        exclusions.extend(self.ignored_offsets(node.label[0], node.text))
        return exclusions

    def calculate_offsets(self, text, applicable_terms, exclusions=None,
                          inclusions=None):
        """Search for defined terms in this text, including singular and
        plural forms of these terms, with a preference for all larger
        (i.e. containing) terms."""

        # don't modify the original
        exclusions = list(exclusions or [])
        inclusions = list(inclusions or [])

        # add singulars and plurals to search terms
        search_terms = {(inflected, t[1])
                        for t in applicable_terms
                        for inflected in self.inflected(t[0])}

        # longer terms first
        search_terms = sorted(search_terms, key=lambda x: len(x[0]),
                              reverse=True)

        matches = []
        for term, ref in search_terms:
            re_term = r'\b' + re.escape(term) + r'\b'
            offsets = [
                (m.start(), m.end())
                for m in re.finditer(re_term, text.lower())]
            safe_offsets = []
            for start, end in offsets:
                #   Start is contained in an existing def
                if any(start >= e[0] and start <= e[1] for e in exclusions):
                    continue
                #   End is contained in an existing def
                if any(end >= e[0] and end <= e[1] for e in exclusions):
                    continue
                safe_offsets.append((start, end))
            if not safe_offsets:
                continue

            exclusions.extend(safe_offsets)
            matches.append((term, ref, safe_offsets))
        return matches
