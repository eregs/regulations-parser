from copy import deepcopy
from itertools import takewhile

from regparser.tree.struct import Node
from regparser.tree.xml_parser.tree_utils import get_node_text


def convert_id(doc_number):
    """Dashes have special significance in other parts of eRegs"""
    return doc_number.replace('-', '_')


def simple_children(elements, deeper_source, label):
    """All paragraphs before the appropriate header can be converted into
    Nodes without further depth analysis or recursion
        :param list[etree.Element] elements:
        :param str deeper_source: SOURCE attribute which indicates a deeper
        header
        :param list[str] label: label of the parent Node"""
    initial_nodes = takewhile(
        lambda e: e.tag != 'HD' or e.get('SOURCE') != deeper_source,
        elements)
    return [Node(text=get_node_text(el), label=label + ['p{}'.format(idx)],
                 node_type='PREAMBLE')
            for idx, el in enumerate(initial_nodes)]


def nested_children(elements, deeper_source, label):
    """Make recursive calls to `make_node` to generate
    children-with-subchildren
        :param list[etree.Element] elements:
        :param str deeper_source: SOURCE attribute which indicates a deeper
        header
        :param list[str] label: label of the parent Node"""
    indexes_of_next_level_headers = [
        idx for idx, elt in enumerate(elements)
        if elt.tag == 'HD' and elt.get('SOURCE') == deeper_source]
    # Pairs of [start, end) indexes, defining runs of XML elements which
    # should be grouped together. The final pair will include len(elements),
    # the end of the list
    start_end_pairs = zip(indexes_of_next_level_headers,
                          indexes_of_next_level_headers[1:] + [len(elements)])
    children = []
    for idx, (start, end) in enumerate(start_end_pairs):
        header = elements[start]
        sub_elements = elements[start + 1:end]
        ident = 'p{}'.format(indexes_of_next_level_headers[0] + idx)
        child = make_node(sub_elements, header.text, label + [ident])
        children.append(child)
    return children


def make_node(elements, title, label):
    """Construct a Node by deriving relationships based on the depth
    associated with HD[@SOURCE] elements
        :param list[etree.Element] elements:
        :param str title: title of the parent Node
        :param list[str] label: label of the parent Node"""
    deeper_source = 'HD{}'.format(len(label))
    children = simple_children(elements, deeper_source, label)
    children += nested_children(elements, deeper_source, label)

    return Node(title=title, label=label, children=children,
                node_type='PREAMBLE')


def parse_preamble(notice_xml):
    """Convert preamble into a Node tree. The preamble is contained within the
    SUPLINF tag, but before a list of altered subjects.
       :param NoticeXML xml: wrapped XML element"""
    suplinf = deepcopy(notice_xml.xpath('.//SUPLINF')[0])
    subject_list = suplinf.xpath('./LSTSUB')
    if subject_list:
        subject_list_idx = suplinf.index(subject_list[0])
        del suplinf[subject_list_idx:]

    title = suplinf[0].text
    label = [convert_id(notice_xml.version_id)]
    return make_node(suplinf[1:], title, label)
