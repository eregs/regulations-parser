import re

import six

from regparser.tree.depth import markers as mtypes
from regparser.tree.depth import optional_rules
from regparser.tree.struct import Node
from regparser.tree.xml_parser import paragraph_processor, tree_utils


class USCodeParagraphMatcher(paragraph_processor.BaseMatcher):
    """Convert a paragraph found in the US Code into appropriate Nodes"""
    _MARKER_RE = re.compile(r'\((?P<marker>[a-z]+|[A-Z]+|[0-9]+)\)')

    def matches(self, xml):
        return xml.tag == 'P'

    def paragraph_markers(self, text):
        """We can't use tree_utils.get_paragraph_markers as that makes
        assumptions about the order of paragraph markers (specifically
        that the markers will match the order found in regulations). This is
        simpler, looking only at multiple markers at the beginning of the
        paragraph"""
        markers = []
        match = self._MARKER_RE.match(text)
        while match:
            markers.append(match.group('marker'))
            text = text[match.end():].strip()
            match = self._MARKER_RE.match(text)
        return markers

    def derive_nodes(self, xml, processor=None):
        nodes = []
        text = tree_utils.get_node_text(xml).strip()
        tagged_text = tree_utils.get_node_text_tags_preserved(xml).strip()
        markers_list = self.paragraph_markers(text)
        with_parens = ['({0})'.format(m) for m in markers_list]
        triplets = zip(markers_list,
                       tree_utils.split_text(text, with_parens),
                       tree_utils.split_text(tagged_text, with_parens))
        for m, text, tagged_text in triplets:
            nodes.append(Node(
                text=text.strip(), label=[m], source_xml=xml,
                tagged_text=six.text_type(tagged_text.strip())
            ))
        return nodes


class USCodeProcessor(paragraph_processor.ParagraphProcessor):
    """ParagraphProcessor which converts a chunk of XML into Nodes. Only
    processes P nodes and limits the type of paragraph markers to those found
    in US Code"""
    MATCHERS = [USCodeParagraphMatcher()]

    def additional_constraints(self):
        return [optional_rules.limit_sequence_gap(),
                optional_rules.limit_paragraph_types(
                    mtypes.lower, mtypes.ints, mtypes.upper, mtypes.roman,
                    mtypes.upper_roman)]


class USCodeMatcher(paragraph_processor.BaseMatcher):
    """Matches a custom `USCODE` tag and parses it's contents with the
    USCodeProcessor. Does not use a custom node type at the moment"""
    def matches(self, xml):
        return xml.tag == 'USCODE'

    def derive_nodes(self, xml, processor=None):
        processor = USCodeProcessor()
        node = Node(label=[mtypes.MARKERLESS], source_xml=xml)
        return [processor.process(xml, node)]
