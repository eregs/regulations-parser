# vim: set fileencoding=utf-8
from collections import defaultdict
import re

import inflection
try:
    key = ('(?i)(p)erson$', '\\1eople')
    del inflection.PLURALS[inflection.PLURALS.index(key)]
except ValueError:
    pass


from regparser.layer import def_finders
from regparser.layer.scope_finder import ScopeFinder
from regparser.layer.layer import Layer
from regparser.tree import struct
from regparser.tree.priority_stack import PriorityStack
import settings


MAX_TERM_LENGTH = 100


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
    def __init__(self, *args, **kwargs):
        Layer.__init__(self, *args, **kwargs)
        self.layer['referenced'] = {}
        #   scope -> List[(term, definition_ref)]
        self.scoped_terms = defaultdict(list)
        self.scope_finder = ScopeFinder()

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
        would replace previous (correct) definitions."""
        applicable_terms = self.applicable_terms(node.label)
        if term in applicable_terms:
            regex = 'the term .?' + re.escape(term) + '.? does not include'
            return bool(re.search(regex, node.text.lower()))
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
            (term, ref) for term, ref in applicable_terms.iteritems()
            if ref.label != node.label_id()]

        exclusions = self.excluded_offsets(node.label_id(), node.text)
        exclusions = self.per_regulation_ignores(
            exclusions, node.label, node.text)

        inclusions = self.included_offsets(node.label_id(), node.text)
        inclusions = self.per_regulation_includes(
            inclusions, node.label, node.text)

        matches = self.calculate_offsets(node.text, term_list, exclusions)
        for term, ref, offsets in matches:
            layer_el.append({
                "ref": ref.term + ':' + ref.label,
                "offsets": offsets
                })
        return layer_el

    def _word_matches(self, term, text):
        """Return the start and end indexes of the term within the text,
        accounting for word boundaries"""
        return [(match.start(), match.end()) for match in
                re.finditer(r'\b' + re.escape(term) + r'\b', text)]

    def per_regulation_ignores(self, exclusions, label, text):
        cfr_part = label[0]
        if settings.IGNORE_DEFINITIONS_IN.get(cfr_part):
            for ignore_term in settings.IGNORE_DEFINITIONS_IN[cfr_part]:
                exclusions.extend(self._word_matches(ignore_term, text))
        return exclusions

    def excluded_offsets(self, label, text):
        """We explicitly exclude certain chunks of text (for example, words
        we are defining shouldn't have links appear within the defined
        term.) More will be added in the future"""
        exclusions = []
        for reflist in self.scoped_terms.values():
            exclusions.extend(
                ref.position for ref in reflist if ref.label == label)
        for ignore_term in settings.IGNORE_DEFINITIONS_IN['ALL']:
            exclusions.extend(self._word_matches(ignore_term, text))
        return exclusions

    def per_regulation_includes(self, inclusions, label, text):
        cfr_part = label[0]
        if settings.INCLUDE_DEFINITIONS_IN.get(cfr_part):
            all_includes = settings.INCLUDE_DEFINITIONS_IN['ALL']
            for included_term, context in all_includes:
                inclusions.extend(self._word_matches(included_term, text))
        return inclusions

    def included_offsets(self, label, text):
        """ We explicitly include certain chunks of text (for example,
            words that the parser doesn't necessarily pick up as being
            defined) that should be part of a defined term """
        inclusions = []
        for included_term, context in settings.INCLUDE_DEFINITIONS_IN['ALL']:
            inclusions.extend(self._word_matches(included_term, text))
        return inclusions

    def calculate_offsets(self, text, applicable_terms, exclusions=[],
                          inclusions=[]):
        """Search for defined terms in this text, including singular and
        plural forms of these terms, with a preference for all larger
        (i.e. containing) terms."""

        # don't modify the original
        exclusions = list(exclusions)
        inclusions = list(inclusions)

        # add singulars and plurals to search terms
        search_terms = set((inflection.singularize(t[0]), t[1])
                           for t in applicable_terms)
        search_terms |= set((inflection.pluralize(t[0]), t[1])
                            for t in applicable_terms)

        # longer terms first
        search_terms = sorted(search_terms, key=lambda x: len(x[0]),
                              reverse=True)

        matches = []
        for term, ref in search_terms:
            re_term = ur'\b' + re.escape(term) + ur'\b'
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
