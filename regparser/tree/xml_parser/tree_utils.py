# -*- coding: utf-8 -*-
from copy import deepcopy
from itertools import chain
import re

from lxml import etree
from six.moves.html_parser import HTMLParser

from regparser.tree.priority_stack import PriorityStack


def prepend_parts(parts_prefix, n):
    """ Recursively preprend parts_prefix to the parts of the node
    n. Parts is a list of markers that indicates where you are in the
    regulation text. """

    n.label = parts_prefix + n.label

    for c in n.children:
        prepend_parts(parts_prefix, c)
    return n


class NodeStack(PriorityStack):
    """ The NodeStack aids our construction of a struct.Node tree. We process
    xml one paragraph at a time; using a priority stack allows us to insert
    items at their proper depth and unwind the stack (collecting children) as
    necessary"""
    def unwind(self):
        """ Unwind the stack, collapsing sub-paragraphs that are on the stack
        into the children of the previous level. """
        children = self.pop()
        parts_prefix = self.peek_last()[1].label
        children = [prepend_parts(parts_prefix, c[1]) for c in children]
        self.peek_last()[1].children = children

    def collapse(self):
        """After all of the nodes have been inserted at their proper levels,
        collapse them into a single root node"""
        while self.size() > 1:
            self.unwind()
        return self.peek_last()[1]


def split_text(text, tokens):
    """
        Given a body of text that contains tokens,
        splice the text along those tokens.
    """
    starts = [text.find(t) for t in tokens]
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    slices = zip(starts, starts[1:])
    texts = [text[i[0]:i[1]] for i in slices] + [text[starts[-1]:]]
    return texts


def _combine_with_space(prev_text, next_text, add_space_if_needed):
    """Logic to determine where to add spaces to XML. Generally this is just
    as matter of checking for space characters, but there are some
    outliers"""
    prev_text, next_text = prev_text or "", next_text or ""
    prev_char, next_char = prev_text[-1:], next_text[:1]
    needs_space = (not prev_char.isspace() and
                   not next_char.isspace() and
                   next_char and
                   prev_char not in u'([/<—-' and
                   next_char not in u').;,]>/—-')
    if add_space_if_needed and needs_space:
        return prev_text + " " + next_text
    else:
        return prev_text + next_text


def replace_xml_node_with_text(node, text):
    """There are some complications w/ lxml when determining where to add the
    replacement text. Account for all of that here."""
    parent, prev = node.getparent(), node.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or '') + text
    else:
        parent.text = (parent.text or '') + text
    parent.remove(node)


def _subscript_to_text(node, add_spaces):
    for e in node.xpath(".//E[@T='52']"):
        text = _combine_with_space("_{" + e.text + "}", e.tail, add_spaces)
        replace_xml_node_with_text(e, text)


def _superscript_to_text(node, add_spaces):
    for e in node.xpath(".//E[@T='51']|.//SU[not(@footnote)]"):
        text = _combine_with_space("^{" + e.text + "}", e.tail, add_spaces)
        replace_xml_node_with_text(e, text)


def _footnotes_to_text(node, add_spaces):
    for su in node.xpath(".//SU[@footnote]"):
        footnote = su.attrib['footnote']
        footnote = footnote.replace('(', r'\(').replace(')', r'\)')
        text = u"[^{}]({})".format(su.text, footnote)
        text = _combine_with_space(text, su.tail, add_spaces)
        replace_xml_node_with_text(su, text)


_whitespace = re.compile(u'\s+', re.UNICODE)    # aware of "thin" spaces, etc.


def get_node_text(node, add_spaces=False):
    """ Extract all the text from an XML node (including the text of it's
    children). """
    node = deepcopy(node)
    _subscript_to_text(node, add_spaces)
    _superscript_to_text(node, add_spaces)
    _footnotes_to_text(node, add_spaces)

    parts = [node.text] + list(
        chain(*([c.text, c.tail] for c in node.getchildren())))
    parts = [_whitespace.sub(' ', part) for part in parts if part]

    final_text = ''
    for part in parts:
        final_text = _combine_with_space(final_text, part, add_spaces)
    return final_text.strip()


_tag_black_list = ('PRTPAGE', )


def get_node_text_tags_preserved(xml_node):
    """Get the body of an XML node as a string, avoiding a specific blacklist
    of bad tags."""
    xml_node = deepcopy(xml_node)
    etree.strip_tags(xml_node, *_tag_black_list)

    # Remove the wrapping tag
    node_text = xml_node.text or ''
    node_text += ''.join(etree.tounicode(child) for child in xml_node)

    node_text = HTMLParser().unescape(node_text)
    return node_text
