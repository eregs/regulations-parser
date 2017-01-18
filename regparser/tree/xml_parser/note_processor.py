import re

from regparser.tree.depth import markers as mtypes
from regparser.tree.depth import optional_rules
from regparser.tree.struct import Node
from regparser.tree.xml_parser import (paragraph_processor,
                                       simple_hierarchy_processor)


class IgnoreNotesHeader(paragraph_processor.BaseMatcher):
    """We don't want to include "Note:" and "Notes:" headers"""
    REGEX = re.compile(r'notes?:?\s*$', re.IGNORECASE)

    def matches(self, xml):
        return xml.tag == 'HD' and self.REGEX.match(xml.text or '')

    def derive_nodes(self, xml, processor=None):
        return []


class NoteProcessor(paragraph_processor.ParagraphProcessor):
    MATCHERS = [simple_hierarchy_processor.DepthParagraphMatcher(),
                IgnoreNotesHeader(),
                paragraph_processor.IgnoreTagMatcher('PRTPAGE')]

    def additional_constraints(self):
        return [optional_rules.limit_paragraph_types(
            mtypes.lower, mtypes.ints, mtypes.roman, mtypes.markerless)]


class NoteMatcher(paragraph_processor.BaseMatcher):
    """Processes the contents of NOTE and NOTES tags using a NoteProcessor"""
    def matches(self, xml):
        return xml.tag in ('NOTE', 'NOTES')

    def derive_nodes(self, xml, processor=None):
        processor = NoteProcessor()
        node = Node(label=[mtypes.MARKERLESS], source_xml=xml,
                    node_type=Node.NOTE)
        return [processor.process(xml, node)]
