import re

import six

from regparser.tree.depth import markers as mtypes
from regparser.tree.depth import optional_rules
from regparser.tree.struct import Node
from regparser.tree.xml_parser import paragraph_processor, tree_utils


class DepthParagraphMatcher(paragraph_processor.BaseMatcher):
    """Convert a paragraph with an optional prefixing paragraph marker into an
    appropriate node. Does not know about collapsed markers nor most types of
    nodes."""
    _MARKER_STR = r'(?P<marker>[a-z]|[ivx]{1,5}|\d{1,2})'
    _PAREN_REGEX = re.compile(r'\({0}\)'.format(_MARKER_STR))
    _PERIOD_REGEX = re.compile(r'{0}\.'.format(_MARKER_STR))

    def matches(self, xml):
        return xml.tag == 'P'

    def derive_nodes(self, xml, processor=None):
        text = tree_utils.get_node_text(xml).strip()
        node = Node(text=text, source_xml=xml)
        node.tagged_text = six.text_type(
            tree_utils.get_node_text_tags_preserved(xml).strip())

        regex = self._PAREN_REGEX if text[:1] == '(' else self._PERIOD_REGEX
        match = regex.match(text)
        if match:
            node.label = [match.group('marker')]
        else:
            node.label = [mtypes.MARKERLESS]

        return [node]


class SimpleHierarchyProcessor(paragraph_processor.ParagraphProcessor):
    """ParagraphProcessor which attempts to pull out whatever paragraph marker
    is available and derive a hierarchy from that."""
    MATCHERS = [DepthParagraphMatcher()]

    def additional_constraints(self):
        return [optional_rules.limit_paragraph_types(
            mtypes.lower, mtypes.ints, mtypes.roman, mtypes.markerless)]


class SimpleHierarchyMatcher(paragraph_processor.BaseMatcher):
    """Detects tags passed to it on init and converts the contents of any
    matches into a hierarchy based on the SimpleHierarchyProcessor. Sets the
    node_type of the subtree's root"""
    def __init__(self, tags, node_type):
        self.tags = list(tags)
        self.node_type = node_type

    def matches(self, xml):
        return xml.tag in self.tags

    def derive_nodes(self, xml, processor=None):
        processor = SimpleHierarchyProcessor()
        node = Node(label=[mtypes.MARKERLESS], source_xml=xml,
                    node_type=self.node_type)
        return [processor.process(xml, node)]
