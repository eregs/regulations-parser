import re
from collections import OrderedDict
from copy import deepcopy
from itertools import takewhile

from lxml import etree

from regparser.tree.depth import heuristics
from regparser.tree.depth.derive import markers as mtypes
from regparser.tree.struct import Node
from regparser.tree.xml_parser.flatsubtree_processor import FlatsubtreeMatcher
from regparser.tree.xml_parser.paragraph_processor import (BaseMatcher,
                                                           GraphicsMatcher,
                                                           IgnoreTagMatcher,
                                                           ParagraphProcessor,
                                                           SimpleTagMatcher,
                                                           TableMatcher)
from regparser.tree.xml_parser.tree_utils import get_node_text

_MARKER_REGEX = re.compile(r'(?P<marker>([0-9]+)|([a-z]+)|([A-Z]+))\.')


def convert_id(doc_number):
    """Dashes have special significance in other parts of eRegs"""
    return doc_number.replace('-', '_')


class PreambleLevelMatcher(BaseMatcher):
    def matches(self, xml):
        return xml.tag == 'PREAMBLE_LEVEL'

    def derive_nodes(self, xml, processor=None):
        """For a given <PREAMBLE_LEVEL>, create a root Node, pull out a
        marker, if present, and recurse via PreambleProcessor on child
        etree.Elements"""
        title = xml.get('TITLE', "")
        marker_match = _MARKER_REGEX.match(title)
        if marker_match:
            label = [marker_match.group('marker')]
        else:
            label = [mtypes.MARKERLESS]
        root = Node(label=label, node_type='preamble', title=title)
        PreambleProcessor().process(xml, root)
        return [root]


class PreambleProcessor(ParagraphProcessor):
    MATCHERS = [PreambleLevelMatcher(), SimpleTagMatcher('P', 'FP'),
                # FTNT's are already converted; we can ignore the original
                IgnoreTagMatcher('FTNT', 'PRTPAGE'), GraphicsMatcher(),
                FlatsubtreeMatcher(tags=['EXTRACT'], node_type=Node.EXTRACT),
                TableMatcher()]

    DEPTH_HEURISTICS = OrderedDict(ParagraphProcessor.DEPTH_HEURISTICS)
    DEPTH_HEURISTICS[heuristics.prefer_diff_types_diff_levels] = 0.2
    DEPTH_HEURISTICS[heuristics.prefer_shallow_depths] = 0.8


def transform_xml(elements, title, depth):
    """The original XML is very _flat_, despite being broken up by headers at
    various depths. This function returns a retooled XML tree with nested
    <PREAMBLE_LEVEL>s; these are much easier for our paragraph processor to
    handle.
    :param list[etree.Element] elements: Initial XML elements to process
    :param str title: Title of the root XML node we'll generate
    :param int depth: indicates which depth headers to look for"""
    root = etree.Element("PREAMBLE_LEVEL", TITLE=title)
    deeper_source = 'HD{0}'.format(depth)
    non_nested_children = takewhile(
        lambda e: e.tag != 'HD' or e.get('SOURCE') != deeper_source,
        elements)
    root.extend(non_nested_children)

    indexes_of_next_level_headers = [
        idx for idx, elt in enumerate(elements)
        if elt.tag == 'HD' and elt.get('SOURCE') == deeper_source]
    # Pairs of [start, end) indexes, defining runs of XML elements which
    # should be grouped together. The final pair will include len(elements),
    # the end of the list
    start_and_ends = zip(indexes_of_next_level_headers,
                         indexes_of_next_level_headers[1:] + [len(elements)])
    header_and_childrens = [(elements[start], elements[start + 1:end])
                            for start, end in start_and_ends]
    for header, children in header_and_childrens:
        title = header.text
        root.append(transform_xml(children, title, depth + 1))

    return root


def parse_intro(notice_xml, doc_id):
    """The introduction to the preamble includes some key paragraphs which
    we bundle together in an "intro" node"""
    root = Node(node_type='preamble_intro', label=[doc_id, 'intro'],
                title='Preamble introduction')
    parent_tags = ('AGY', 'ACT', 'SUM', 'DATES', 'ADD', 'FURINF')
    xpath = '|'.join('.//' + parent_tag for parent_tag in parent_tags)
    for xml in notice_xml.xpath(xpath):
        title = xml.xpath('./HD')[0].text.strip()
        paras = [get_node_text(p) for p in xml.xpath("./P")]
        parent_label = [doc_id, 'intro', 'p{0}'.format(len(root.children) + 1)]
        children = []
        for i, para in enumerate(paras, start=1):
            label = [doc_id, 'intro', 'p{0}'.format(len(root.children) + 1),
                     'p{0}'.format(i)]
            children.append(Node(text=para, node_type='preamble', label=label))
        root.children.append(Node(node_type='preamble', label=parent_label,
                                  title=title, children=children))
    if root.children:
        return root


def parse_preamble(notice_xml):
    """Convert preamble into a Node tree. The preamble is contained within the
    SUPLINF tag, but before a list of altered subjects. Processing proceeds in
    two phases: first we make the XML more hierarchical, then we use that
    hierarchy to create nested nodes
       :param NoticeXML xml: wrapped XML element"""
    suplinf = deepcopy(notice_xml.xpath('.//SUPLINF')[0])
    subject_list = suplinf.xpath('./LSTSUB')
    if subject_list:
        subject_list_idx = suplinf.index(subject_list[0])
        del suplinf[subject_list_idx:]

    title = suplinf[0].text
    label = [convert_id(notice_xml.version_id)]
    root = transform_xml(suplinf[1:], title, depth=1)
    root_node = Node(node_type='preamble', label=label, title=title)
    PreambleProcessor().process(root, root_node)
    intro = parse_intro(notice_xml, label[0])
    if intro:
        root_node.children.insert(0, intro)
    return root_node
