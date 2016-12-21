# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import itertools
import logging
import re

from interpparser.tree import merge_labels, text_to_labels
from regparser.citations import Label, remove_citation_overlaps
from regparser.layer.key_terms import KeyTerms
from regparser.tree.depth import heuristics, rules, markers as mtypes
from regparser.tree.depth.derive import derive_depths
from regparser.tree.struct import Node, treeify
from regparser.tree.xml_parser import matchers, tree_utils


logger = logging.getLogger(__name__)
_marker_regex = re.compile(
    r'^\s*(' +                 # line start
    '([0-9]+)' +               # digits
    '|([ivxlcdm]+)' +          # roman
    '|([A-Z]+)' +              # upper
    '|(<E[^>]*>[0-9]+)' +      # emphasized digit
    r')\s*\..*', re.DOTALL)    # followed by a period and then anything


_marker_stars_regex = re.compile(
    r'^\s*(' +                 # line start
    '([0-9]+)' +               # digits
    '|([ivxlcdm]+)' +          # roman
    '|([A-Z]+)' +              # upper
    '|(<E[^>]*>[0-9]+)' +      # emphasized digit
    r')\s+\* \* \*\s*$', re.DOTALL)  # followed by stars


def get_first_interp_marker(text):
    match = _marker_regex.match(text)
    if match:
        marker = text[:text.find('.')].strip()      # up to dot
        if '<' in marker:
            marker += '</E>'
        return marker
    match = _marker_stars_regex.match(text)
    if match:
        return text[:text.find('*')].strip()        # up to star


_first_markers = [re.compile(r'[\.|,|;|:|\-|—]\s*(' + marker + r')\.')
                  for marker in ['i', 'A', '1']]


def collapsed_markers_matches(node_text, tagged_text):
    """Find collapsed markers, i.e. tree node paragraphs that begin within a
    single XML node, within this text. Remove citations and other false
    positives. This is pretty hacky right now -- it focuses on the plain
    text but takes cues from the tagged text. @todo: streamline logic"""
    # In addition to the regex above, keyterms are an acceptable prefix. We
    # therefore convert keyterms to satisfy the above regex
    node_for_keyterms = Node(
        node_text, node_type=Node.INTERP, tagged_text=tagged_text,
        label=[get_first_interp_marker(node_text)]
    )
    keyterm = KeyTerms.keyterm_in_node(node_for_keyterms)
    if keyterm:
        node_text = node_text.replace(keyterm, '.' * len(keyterm))

    collapsed_markers = []
    for marker in _first_markers:
        possible = [(m, m.start(), m.end())
                    for m in marker.finditer(node_text)]
        possible = remove_citation_overlaps(node_text, possible)
        possible = [triplet[0] for triplet in possible]
        collapsed_markers.extend(
            match for match in possible
            if not false_collapsed_marker(match, node_text, tagged_text)
        )
    return collapsed_markers


def false_collapsed_marker(match, node_text, tagged_text):
    """Is the provided regex match a false positive -- it looks like an
    interpretation paragraph marker, but isn't actually?"""
    if match.start() == 0:     # not a collapsed marker
        return True
    # If certain characters follow, kill it
    tail = node_text[match.end():]
    if any(tail.startswith(c) for c in ("e.", ")", "”", '"', "'")):
        return True
    # As all "1." collapsed markers must be emphasized, run a quick
    # check to weed out some false positives
    if '<E T="03">1' not in tagged_text and match.group(1) == '1':
        return True
    return False


def _non_hed(xml_node):
    """E.g. <HD SOURCE="H2">Text here</HD>"""
    return xml_node.tag.upper() == 'HD' and xml_node.attrib['SOURCE'] != 'HED'


def _p_with_label_in_child(xml_node):
    """E.g. <P><E>22(a)</E>.</P>"""
    children = xml_node.getchildren()
    return (
        xml_node.tag.upper() == 'P' and
        not (xml_node.text or '').strip() and
        len(children) == 1 and
        not (children[0].tail or '').strip(" \n\t.") and
        text_to_labels(children[0].text, Label(), warn=False)
    )


def _non_interp_p_with_label(xml_node):
    """E.g. <P>22(a)</P> but not <P>ii. 22(a)</P>"""
    return (
        xml_node.tag.upper() == 'P' and
        not xml_node.getchildren() and
        xml_node.text and not get_first_interp_marker(xml_node.text) and
        text_to_labels(xml_node.text, Label(), warn=False, force_start=True)
    )


def is_title(xml_node):
    """Not all titles are created equal. Sometimes a title appears as a
    paragraph tag, mostly to add confusion."""
    return (
        _non_hed(xml_node) or
        _p_with_label_in_child(xml_node) or
        _non_interp_p_with_label(xml_node)
    )


def process_inner_children(inner_stack, xml_node):
    """Process the following nodes as children of this interpretation. This
    is very similar to reg_text.py:build_from_section()"""
    children = itertools.takewhile(
        lambda x: not is_title(x), xml_node.itersiblings())
    nodes = []
    for xml_node in filter(lambda c: c.tag in ('P', 'STARS'), children):
        node_text = tree_utils.get_node_text(xml_node, add_spaces=True)
        text_with_tags = tree_utils.get_node_text_tags_preserved(xml_node)
        first_marker = get_first_interp_marker(text_with_tags)
        if xml_node.tag == 'STARS':
            nodes.append(Node(label=[mtypes.STARS_TAG]))
        elif not first_marker and nodes:
            logger.warning("Couldn't determine interp marker. Appending to "
                           "previous paragraph: %s", node_text)
            previous = nodes[-1]
            previous.text += "\n\n" + node_text
            if previous.tagged_text:
                previous.tagged_text += "\n\n" + text_with_tags
            else:
                previous.tagged_text = text_with_tags
        else:
            nodes.extend(nodes_from_interp_p(xml_node))

    # Trailing stars don't matter; slightly more efficient to ignore them
    while nodes and nodes[-1].label[0] in mtypes.stars:
        nodes = nodes[:-1]

    add_nodes_to_stack(nodes, inner_stack)


def nodes_from_interp_p(xml_node):
    """Given an XML node that contains text for an interpretation paragraph,
    split it into sub-paragraphs and account for trailing stars"""
    node_text = tree_utils.get_node_text(xml_node, add_spaces=True)
    text_with_tags = tree_utils.get_node_text_tags_preserved(xml_node)
    first_marker = get_first_interp_marker(text_with_tags)
    collapsed = collapsed_markers_matches(node_text, text_with_tags)

    #   -2 throughout to account for matching the character + period
    ends = [m.end() - 2 for m in collapsed[1:]] + [len(node_text)]
    starts = [m.end() - 2 for m in collapsed] + [len(node_text)]

    #   Node for this paragraph
    n = Node(node_text[0:starts[0]], label=[first_marker],
             node_type=Node.INTERP, tagged_text=text_with_tags)
    yield n
    if n.text.endswith('* * *'):
        yield Node(label=[mtypes.INLINE_STARS])

    #   Collapsed-marker children
    for match, end in zip(collapsed, ends):
        marker = match.group(1)
        if marker == '1':
            marker = '<E T="03">1</E>'
        n = Node(node_text[match.end() - 2:end], label=[marker],
                 node_type=Node.INTERP)
        yield n
        if n.text.endswith('* * *'):
            yield Node(label=[mtypes.INLINE_STARS])


def add_nodes_to_stack(nodes, inner_stack):
    """Calculate most likely depth assignments to each node; add to the
    provided stack"""
    # Use constraint programming to figure out possible depth assignments
    depths = derive_depths(
        [node.label[0] for node in nodes],
        [rules.depth_type_order([(mtypes.ints, mtypes.em_ints),
                                 (mtypes.roman, mtypes.upper),
                                 mtypes.upper, mtypes.em_ints,
                                 mtypes.em_roman])])
    if depths:
        # Find the assignment which violates the least of our heuristics
        depths = heuristics.prefer_multiple_children(depths, 0.5)
        depths = sorted(depths, key=lambda d: d.weight, reverse=True)
        depths = depths[0]
        for node, par in zip(nodes, depths):
            if par.typ != mtypes.stars:
                last = inner_stack.peek()
                node.label = [l.replace('<E T="03">', '').replace('</E>', '')
                              for l in node.label]
                if len(last) == 0:
                    inner_stack.push_last((3 + par.depth, node))
                else:
                    inner_stack.add(3 + par.depth, node)


def missing_levels(last_label, label):
    """Sometimes we will have a 2(a)(1) without seeing 2(a). Fill in the
    missing level"""
    #   Only care about data before 'Interp'
    label = list(itertools.takewhile(lambda l: l != Node.INTERP_MARK, label))
    #   Find only the shared segments
    zipped = zip(last_label, label)
    shared = list(itertools.takewhile(lambda pair: pair[0] == pair[1], zipped))

    missing = []
    #   Add layers in between, but do not add the last; e.g. add 2(a) but
    #   not 2(a)(1)
    for i in range(len(shared) + 1, len(label)):
        level_label = label[:i] + [Node.INTERP_MARK]
        missing.append(Node(node_type=Node.INTERP, label=level_label))
    return missing


def parse_from_xml(root, xml_nodes):
    """Core of supplement processing; shared by whole XML parsing and notice
    parsing. root is the root interpretation node (e.g. a Node with label
    '1005-Interp'). xml_nodes contains all XML nodes which will be relevant
    to the interpretations"""
    supplement_nodes = [root]

    last_label = root.label
    header_count = 0
    for ch in xml_nodes:
        node = Node(label=last_label, node_type=Node.INTERP)
        label_obj = Label.from_node(node)

        #   Explicitly ignore "subpart" headers, as they are inconsistent
        #   and they will be reconstructed as subterps client-side
        text = tree_utils.get_node_text(ch, add_spaces=True)
        if is_title(ch) and 'subpart' not in text.lower():
            labels = text_to_labels(text, label_obj)
            if labels:
                label = merge_labels(labels)
            else:   # Header without a label, like an Introduction, etc.
                header_count += 1
                label = root.label[:2] + ['h%d' % header_count]

            inner_stack = tree_utils.NodeStack()
            missing = missing_levels(last_label, label)
            supplement_nodes.extend(missing)
            last_label = label

            node = Node(node_type=Node.INTERP, label=label,
                        title=text.strip())
            inner_stack.add(2, node)

            process_inner_children(inner_stack, ch)

            while inner_stack.size() > 1:
                inner_stack.unwind()

            ch_node = inner_stack.m_stack[0][0][1]
            supplement_nodes.append(ch_node)

    supplement_tree = treeify(supplement_nodes)

    def per_node(node):
        node.label = [l.replace('<E T="03">', '') for l in node.label]
        for child in node.children:
            per_node(child)
    for node in supplement_tree:
        per_node(node)

    return supplement_tree[0]


def build_supplement_tree(reg_part, node):
    """ Build the tree for the supplement section. """
    title = get_app_title(node)
    root = Node(
        node_type=Node.INTERP,
        label=[reg_part, Node.INTERP_MARK],
        title=title)

    return parse_from_xml(root, node.getchildren())


@matchers.match_tag('INTERP')
def parse_interp(parent, xml_node):
    parent.children.append(build_supplement_tree(parent.cfr_part, xml_node))


def get_app_title(node):
    """ Appendix/Supplement sections have the title in an HD tag, or
    if they are reserved, in a <RESERVED> tag. Extract the title. """

    titles = node.xpath("./HD[@SOURCE='HED']")
    if titles:
        return titles[0].text
    else:
        return node.xpath("./RESERVED")[0]
