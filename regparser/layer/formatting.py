"""Find and abstracts formatting information from the regulation tree. In many
ways, this is like a markdown parser."""
import abc
import re
from collections import OrderedDict

import six
from lxml import etree

from regparser.layer.layer import Layer
from regparser.tree import struct
from regparser.tree.priority_stack import PriorityStack
from regparser.tree.xml_parser import tree_utils


class HeaderStack(PriorityStack):
    """Used to determine Table Headers -- indeed, they are complicated
    enough to warrant their own stack"""
    def unwind(self):
        children = [pair[1] for pair in self.pop()]
        self.peek_last()[1].children = children


class TableHeaderNode(object):
    """Represents a cell in a table's header"""
    def __init__(self, text, level):
        self.text = text
        self.level = level
        self.children = []

    def height(self):
        child_heights = [0] + [c.height() for c in self.children]
        return 1 + max(child_heights)

    def width(self):
        if not self.children:
            return 1
        return sum(c.width() for c in self.children)


def build_header(xml_nodes):
    """Builds a TableHeaderNode tree, with an empty root. Each node in the tree
    includes its colspan/rowspan"""
    def add_element(stack, xml_node, level=None):
        text = tree_utils.get_node_text(xml_node, add_spaces=True).strip()
        stack.add(level, TableHeaderNode(text, level))

    stack = HeaderStack()
    stack.add(0, TableHeaderNode(None, 0))  # Root

    for xml_node in xml_nodes:
        level = int(xml_node.attrib['H'])
        add_element(stack, xml_node, level=level)

    while stack.size() > 1:
        stack.unwind()
    root = stack.m_stack[0][0][1]

    max_height = root.height()

    def set_colspan(n):
        n.colspan = n.width()
    struct.walk(root, set_colspan)

    root = build_header_rowspans(root, max_height)

    return root


def build_header_rowspans(tree_root, max_height):
    """
    The following table is an example of why we need a relatively complicated
    approach to setting rowspan:

    |R1C1     |R1C2               |
    |R2C1|R2C2|R2C3     |R2C4     |
    |    |    |R3C1|R3C2|R3C3|R3C4|

    If we set the rowspan of each node to::

        max_height - node.height() - node.level + 1

    R1C1 will end up with a rowspan of 2 instead of 1, because of difficulties
    handling the implicit rowspans for R2C1 and R2C2.

    Instead, we generate a list of the paths to each leaf and then set
    rowspan based on that.

    Rowspan for leaves is ``max_height - node.height() - node.level + 1``, and
    for root is simply 1. Other nodes' rowspans are set to the level of the
    node after them minus their own level.
    """

    paths = []

    def collect_paths(node, path):
        if node.children:
            for child in node.children:
                collect_paths(child, path + [node])
        else:
            paths.append(path + [node])
    collect_paths(tree_root, [])

    for path in paths:
        for i, node in enumerate(path):
            if i == 0:  # root
                node.rowspan = 1
            elif i + 1 == len(path):    # leaves
                node.rowspan = max_height - node.height() - node.level + 1
            else:   # intermediate nodes
                node.rowspan = path[i + 1].level - node.level

    return tree_root


def table_xml_to_plaintext(xml_node):
    """Markdown representation of a table. Note that this doesn't account
    for all the options needed to display the table properly, but works fine
    for simple tables. This gets included in the reg plain text"""
    header = [tree_utils.get_node_text(hd, add_spaces=True).strip()
              for hd in xml_node.xpath('./BOXHD/CHED|./TTITLE')]
    divider = ['---'] * len(header)
    rows = []
    for tr in xml_node.xpath('./ROW'):
        rows.append([tree_utils.get_node_text(td, add_spaces=True).strip()
                     for td in tr.xpath('./ENT')])
    table = []
    for row in [header] + [divider] + rows:
        table.append('|' + '|'.join(row) + '|')
    return '\n'.join(table)


def table_xml_to_data(xml_node):
    """Construct a data structure of the table data. We provide a different
    structure than the native XML as the XML encodes too much logic. This
    structure can be used to generate semi-complex tables which could not be
    generated from the markdown above"""
    header_root = build_header(xml_node.xpath('./BOXHD/CHED'))
    header = [[] for _ in range(header_root.height())]

    def per_node(node):
        header[node.level].append({'text': node.text,
                                   'colspan': node.colspan,
                                   'rowspan': node.rowspan})
    struct.walk(header_root, per_node)
    header = header[1:]     # skip the root

    rows = []
    for row in xml_node.xpath('./ROW'):
        rows.append([tree_utils.get_node_text(td, add_spaces=True).strip()
                     for td in row.xpath('./ENT')])

    table_data = {'header': header, 'rows': rows}

    caption_nodes = xml_node.xpath('./TTITLE')
    if len(caption_nodes):
        text = tree_utils.get_node_text(caption_nodes[0]).strip()
        table_data["caption"] = text

    return table_data


class PlaintextFormatData(six.with_metaclass(abc.ABCMeta)):
    """Base class for formatting information which can be derived from the
    plaintext of a regulation node"""
    @abc.abstractproperty
    def REGEX(self):    # noqa - this is a property
        """Regular expression used to find matches in the plain text"""
        raise NotImplementedError()

    @abc.abstractmethod
    def match_data(self, match):
        """Derive data structure (as a dict) from the regex match"""
        raise NotImplementedError()

    def process(self, text):
        """Find all matches of self.REGEX, transform them into the appropriate
        data structure, return these as a list"""
        # [string] -> (match object, count)
        match_text_counter = OrderedDict()
        for match in self.REGEX.finditer(text):
            match_text = match.group(0)
            existing = match_text_counter.get(match_text, (None, 0))
            count = existing[1]
            match_text_counter[match_text] = (match, count + 1)

        for match, count in match_text_counter.values():
            data = {'text': match.group(0),
                    'locations': list(range(count))}
            data.update(self.match_data(match))
            yield data


class FencedData(PlaintextFormatData):
    """E.g.
        ```note
        Line 1
        Line 2
        ```
    """
    REGEX = re.compile(r"```(?P<type>[a-zA-Z0-9 ]+)\w*\n"
                       r"(?P<lines>([^\n]*\n)+)"
                       r"```")

    def match_data(self, match):
        return {'fence_data': {
            'type': match.group('type'),
            'lines': [l for l in match.group('lines').split("\n") if l]
        }}


class Subscript(PlaintextFormatData):
    """E.g.     a_{0}"""
    REGEX = re.compile(r"_\{(?P<subscript>[^\}]+)\}")

    def match_data(self, match):
        return {'subscript_data': {'subscript': match.group('subscript')}}


class Superscript(PlaintextFormatData):
    """E.g.     x^{2}"""
    REGEX = re.compile(r"\^\{(?P<superscript>[^\}]+)\}")

    def match_data(self, match):
        return {
            'superscript_data': {'superscript': match.group('superscript')}}


class Dashes(PlaintextFormatData):
    """E.g.     Some text some text_____"""
    REGEX = re.compile(r"(?P<text>.*)(?P<dashes>_{5,})$")

    def match_data(self, match):
        return {'dash_data': {'text': match.group('text')}}


class Footnotes(PlaintextFormatData):
    """E.g.     [^4](Contents of footnote)
       The footnote may also contain parens if they are escaped with a
       backslash"""
    # Note: we don't want to use \(\) is the example in the docstring as we'd
    # need to double-escape or mark the docstring as raw.

    _ref_regex = r"\[\^(?P<ref>[^\]]*)\]"   # [^\]]* = take until hitting a ]
    _begin_note_regex = r"\((?P<note>.*?)"
    _close_paren = r"(?<!\\)\)"     # neg lookbehind for skipping escaped \)
    REGEX = re.compile(_ref_regex + _begin_note_regex + _close_paren)

    def match_data(self, match):
        # Un-escape parens
        note = match.group('note').replace(r'\(', '(').replace(r'\)', ')')
        return {'footnote_data': {'ref': match.group('ref'), 'note': note}}


def node_to_table_xml_els(node):
    """Search in a few places for GPOTABLE xml elements"""
    if node.source_xml is not None:
        root_xml_el = node.source_xml
    else:
        # tagged_text isn't quite XML -- it's often a fragment with unescaped
        # characters. Clean it up before searching it
        tagged_text = node.tagged_text.replace('&', '&amp;')
        tagged_text = u'<ROOT>{0}</ROOT>'.format(tagged_text)
        root_xml_el = etree.fromstring(tagged_text)

    return root_xml_el.xpath('self::GPOTABLE|.//GPOTABLE')


class Formatting(Layer):
    """Layer responsible for tables, subscripts, and other formatting-related
    information"""
    shorthand = 'formatting'

    def process(self, node):
        layer_el = []
        for table_el in node_to_table_xml_els(node):
            layer_el.append({'text': table_xml_to_plaintext(table_el),
                             'locations': [0],
                             'table_data': table_xml_to_data(table_el)})

        for finder_class in PlaintextFormatData.__subclasses__():
            layer_el.extend(finder_class().process(node.text))

        if layer_el:
            return layer_el
