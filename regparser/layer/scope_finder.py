from collections import defaultdict
import re

from regparser.citations import internal_citations, Label
from regparser.tree import struct


class ScopeFinder(object):
    """Useful for determining the scope of a term"""
    #   Regexes used in determining scope
    _PART_RE, _SUBPART_RE = re.compile(r"\bpart\b"), re.compile(r"\bsubpart\b")
    _SECT_RE = re.compile(r"\bsection\b")
    _PAR_RE = re.compile(r"\bparagraph\b")
    #   Regex to confirm scope indicator
    _SCOPE_RE = re.compile(r".*purposes of( this)?\s*$", re.DOTALL)
    _SCOPE_USED_RE = re.compile(
        r".*as used in( this)?\s*$", re.DOTALL | re.IGNORECASE)

    def __init__(self):
        #   subpart -> list[section]
        self.subpart_map = defaultdict(list)

    def add_subparts(self, root):
        """Document the relationship between sections and subparts"""
        # Need a reference for maintaining state
        self.__current_subpart = None
        struct.walk(root, self._subpart_per_node)

    def _subpart_per_node(self, node):
        with struct.node_type_cases(node.node_type) as case:
            if case.match(struct.Node.SUBPART):
                self.__current_subpart = node.label[2]
            if case.match(struct.Node.EMPTYPART):
                self.__current_subpart = None
            if case.match(struct.Node.REGTEXT, struct.Node.APPENDIX):
                if len(node.label) == 2:
                    # Subparts
                    section = node.label[-1]
                    self.subpart_map[self.__current_subpart].append(section)
            case.ignore(struct.Node.INTERP, struct.Node.EXTRACT)

    def scope_of_text(self, text, label_struct, verify_prefix=True):
        """Given specific text, try to determine the definition scope it
        indicates. Implicit return None if none is found."""
        scopes = []
        #   First, make a list of potential scope indicators
        citations = internal_citations(text, label_struct, require_marker=True)
        indicators = [(c.full_start, c.label.to_list()) for c in citations]
        text = text.lower()
        label_list = label_struct.to_list()
        indicators.extend((m.start(), label_list[:1])
                          for m in self._PART_RE.finditer(text))
        indicators.extend((m.start(), label_list[:2])
                          for m in self._SECT_RE.finditer(text))
        indicators.extend((m.start(), label_list)
                          for m in self._PAR_RE.finditer(text))
        #   Subpart's a bit more complicated, as it gets expanded into a
        #   list of sections
        for match in self._SUBPART_RE.finditer(text):
            indicators.extend(
                (match.start(), subpart_label)
                for subpart_label in self.subpart_scope(label_list))

        #   Finally, add the scope if we verify its prefix
        for start, label in indicators:
            if not verify_prefix or self._SCOPE_RE.match(text[:start]):
                scopes.append(label)
            elif self._SCOPE_USED_RE.match(text[:start]):
                scopes.append(label)

        #   Add interpretation to scopes
        scopes = scopes + [s + [struct.Node.INTERP_MARK] for s in scopes]
        if scopes:
            return [tuple(s) for s in scopes]

    def subpart_scope(self, label_parts):
        """Given a label, determine which sections fall under the same
        subpart"""
        reg = label_parts[0]
        section = label_parts[1]
        for subpart in self.subpart_map:
            if section in self.subpart_map[subpart]:
                return [[reg, sect] for sect in self.subpart_map[subpart]]
        return []

    def determine_scope(self, stack):
        for node in stack.lineage():
            scopes = self.scope_of_text(node.text, Label.from_node(node))
            if scopes:
                return [tuple(s) for s in scopes]

        #   Couldn't determine scope; default to the entire reg
        return [tuple(node.label[:1])]
