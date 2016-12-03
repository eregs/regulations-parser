# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import namedtuple

from lxml import etree
import pytest

from regparser.test_utils.node_accessor import NodeAccessor
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.depth import markers as mtypes
from regparser.tree.gpo_cfr import section
from regparser.tree.struct import Node


def test_get_markers():
    text = '(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
    assert section.get_markers(text, mtypes.STARS_TAG) == ['a', '1']


def test_get_markers_bad_citation():
    text = (
        '(vi)<E T="03">Keyterm.</E>The information required by paragraphs '
        '(a)(2), (a)(4)(iii), (a)(5), (b) through (d), (f), and (g) with '
        'respect to something, (i), (j), (l) through (p), (q)(1), and (r) '
        'with respect to something.'
    )
    assert section.get_markers(text) == ['vi']


def test_get_markers_collapsed():
    """Only find collapsed markers if they are followed by a marker in
    sequence"""
    text = '(a) <E T="03">aaa</E>—(1) 111. (i) iii'
    assert section.get_markers(text) == ['a']
    assert section.get_markers(text, 'b') == ['a']
    assert section.get_markers(text, 'A') == ['a', '1', 'i']
    assert section.get_markers(text, 'ii') == ['a', '1', 'i']
    assert section.get_markers(text, mtypes.STARS_TAG) == ['a', '1', 'i']
    assert section.get_markers(text, '2') == ['a', '1']


@pytest.mark.parametrize('text,expected', [
    ('(k)(2)(iii) abc (j)', ['k', '2', 'iii']),
    ('(i)(A) The minimum period payment', ['i', 'A'])
])
def test_initial_markers(text, expected):
    """Should not find any collapsed markers and should find all of the
    markers at the beginning of the text"""
    assert list(section.initial_markers(text)) == expected


@pytest.mark.parametrize('text,expected', [
    ('(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow', ['1']),
    ('(a) <E T="03">Blah </E>means (1) <E T="03">Notice.</E> follow', ['1']),
    ('(1) See paragraph (a) for more', []),
    ('(a) (1) More content', []),
    ('(a) <E T="03">Transfer—</E>(1) <E T="03">Notice.</E> follow', ['1']),
    ('(a) <E T="03">Keyterm</E>—(1)(i) Content', ['1', 'i']),
    ('(C) The information required by paragraphs (a)(2), (a)(4)(iii), '
     '(a)(5), (b) through (d), (i), (l) through (p)', []),
])
def test_collapsed_markers(text, expected):
    """We're expecting to find collapsed markers when they have certain
    prefixes, but not when they are part of a citation or do not have the
    appropriate prefix"""
    assert section.collapsed_markers(text) == expected


def test_next_marker_found():
    """Find the first paragraph marker following a paragraph"""
    with XMLBuilder("ROOT") as ctx:
        ctx.P("(A) AAA")
        ctx.PRTPART()
        ctx.P("(d) ddd")
        ctx.P("(1) 111")
    assert section.next_marker(ctx.xml[0]) == 'd'


def test_next_marker_stars():
    """STARS tag has special significance."""
    with XMLBuilder("ROOT") as ctx:
        ctx.P("(A) AAA")
        ctx.PRTPART()
        ctx.STARS()
        ctx.P("(d) ddd")
        ctx.P("(1) 111")
    assert section.next_marker(ctx.xml[0]) == mtypes.STARS_TAG


def test_next_marker_none():
    """If no marker is present, return None"""
    with XMLBuilder("ROOT") as ctx:
        ctx.P("(1) 111")
        ctx.P("Content")
        ctx.P("(i) iii")
    assert section.next_marker(ctx.xml[0]) is None


Expected = namedtuple('Expected', ['markers', 'result_text', 'tagged'])


@pytest.mark.parametrize('text,expected', [
    ('(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow',
     Expected(markers=('a', '1'),
              result_text=('(a) Transfer —', '(1) Notice. follow'),
              tagged=('(a) <E T="03">Transfer </E>—',
                      '(1) <E T="03">Notice.</E> follow'))),
    ('(A) aaaa. (<E T="03">1</E>) 1111',
     Expected(markers=('A', '<E T="03">1</E>'),
              result_text=('(A) aaaa. ', '(1) 1111'),
              tagged=('(A) aaaa. ', '(<E T="03">1</E>) 1111'))),
    # Don't treat a single marker differently than multiple, there might
    # be prefix text
    ('Words then. (a) a subparagraph',
     Expected(markers=(mtypes.MARKERLESS, 'a'),
              result_text=('Words then. ', '(a) a subparagraph'),
              tagged=('Words then. ', '(a) a subparagraph')))
])
def test_split_by_markers(text, expected):
    xml = etree.fromstring('<ROOT><P>{}</P><STARS/></ROOT>'.format(text))
    results = section.split_by_markers(xml[0])
    results = list(zip(*results))    # unzips...
    assert results == list(expected)


def test_process_markerless_collapsed():
    """Should be able to find collapsed markers in a markerless paragraph"""
    with XMLBuilder("ROOT") as ctx:
        ctx.P("Intro text")
        ctx.child_from_string(
            '<P><E T="03">Some term.</E> (a) First definition</P>')
        ctx.P("(b) Second definition")
    root = Node(label=['111', '22'])
    root = section.RegtextParagraphProcessor().process(ctx.xml, root)
    root = NodeAccessor(root)

    assert root.label == ['111', '22']
    assert len(root.children) == 2
    assert all(c.is_markerless for c in root.children)
    keyterm_label = root.child_labels[1]
    assert len(keyterm_label) > 5
    assert root[keyterm_label].child_labels == ['a', 'b']


def test_process_nested_uscode():
    with XMLBuilder("ROOT") as ctx:
        ctx.P("Some intro")
        with ctx.EXTRACT():
            ctx.HD("The U.S. Code!")
            with ctx.USCODE():
                ctx.P("(x)(1) Some content")
                ctx.P("(A) Sub-sub-paragraph")
                ctx.P("(i)(I) Even more nested")
    root = section.RegtextParagraphProcessor().process(ctx.xml, Node())
    root = NodeAccessor(root)

    assert root['p1'].text == "Some intro"
    assert root['p2']['p1'].title == 'The U.S. Code!'
    code = root['p2']['p2']
    assert code.source_xml.tag == 'USCODE'
    assert code['x'].text == '(x)'
    assert code['x']['1'].text == '(1) Some content'
    assert code['x']['1']['A'].text == '(A) Sub-sub-paragraph'
    assert code['x']['1']['A']['i'].text == '(i)'
    assert code['x']['1']['A']['i']['I'].text == '(I) Even more nested'
