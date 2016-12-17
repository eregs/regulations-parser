# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from lxml import etree

from interpparser import gpo_cfr
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser import tree_utils


def test_interpretation_markers():
    text = '1. Kiwis and Mangos'
    assert gpo_cfr.get_first_interp_marker(text) == '1'


def test_interpretation_markers_roman():
    text = 'iv. Kiwis and Mangos'
    assert gpo_cfr.get_first_interp_marker(text) == 'iv'


def test_interpretation_markers_emph():
    text = '<E T="03">1.</E> Kiwis and Mangos'
    assert gpo_cfr.get_first_interp_marker(text) == '<E T="03">1</E>'

    text = '<E T="03">1. Kiwis and Mangos.</E> More content.'
    assert gpo_cfr.get_first_interp_marker(text) == '<E T="03">1</E>'


def test_interpretation_markers_none():
    text = '(iv) Kiwis and Mangos'
    assert gpo_cfr.get_first_interp_marker(text) is None


def test_interpretation_markers_stars_no_period():
    for marker in ('4 ', 'iv  ', 'A\t'):
        text = marker + '* * *'
        assert gpo_cfr.get_first_interp_marker(text) == marker.strip()

        text = "33 * * * Some more stuff"
        assert gpo_cfr.get_first_interp_marker(text) is None


def test_build_supplement_tree():
    """Integration test"""
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Supplement I to Part 737-Official Interpretations",
               SOURCE='HED')
        ctx.HD("Section 737.5 NASCAR", SOURCE='HD2')
        ctx.P("1. Paragraph 1")
        ctx.P("i. Paragraph i; A. Start of A")
        ctx.HD("5(a) Access Device", SOURCE='HD2')
        ctx.P("1. Paragraph 111")
        ctx.P("i. Content content")
        ctx.P("ii. More content")
        ctx.P("A. Aaaaah")
        ctx.child_from_string('<P><E T="03">1.</E> More info</P>')
        ctx.child_from_string('<P><E T="03">2.</E> Second info</P>')
        ctx.child_from_string('<P><E T="03">3. Keyterms</E></P>')
    tree = gpo_cfr.build_supplement_tree('737', ctx.xml)
    assert tree.label == ['737', 'Interp']
    assert len(tree.children) == 1

    i5 = tree.children[0]
    assert i5.label == ['737', '5', 'Interp']
    assert len(i5.children) == 2

    i51, i5a = i5.children
    assert i51.label == ['737', '5', 'Interp', '1']
    assert len(i51.children) == 1
    i51i = i51.children[0]
    assert i51i.label == ['737', '5', 'Interp', '1', 'i']
    assert len(i51i.children) == 1
    i51ia = i51i.children[0]
    assert i51ia.label == ['737', '5', 'Interp', '1', 'i', 'A']
    assert i51ia.children == []

    assert i5a.label == ['737', '5', 'a', 'Interp']
    assert len(i5a.children) == 1
    i5a1 = i5a.children[0]
    assert i5a1.label == ['737', '5', 'a', 'Interp', '1']
    assert len(i5a1.children) == 2
    i5a1i, i5a1ii = i5a1.children
    assert i5a1i.label == ['737', '5', 'a', 'Interp', '1', 'i']
    assert i5a1i.children == []

    assert i5a1ii.label == ['737', '5', 'a', 'Interp', '1', 'ii']
    assert len(i5a1ii.children) == 1
    i5a1iia = i5a1ii.children[0]
    assert i5a1iia.label == ['737', '5', 'a', 'Interp', '1', 'ii', 'A']
    assert len(i5a1iia.children) == 3
    i5a1iia1, i5a1iia2, i5a1iia3 = i5a1iia.children
    assert i5a1iia1.label == ['737', '5', 'a', 'Interp', '1', 'ii', 'A', '1']
    assert i5a1iia1.tagged_text == '<E T="03">1.</E> More info'
    assert i5a1iia1.children == []
    assert i5a1iia2.label == ['737', '5', 'a', 'Interp', '1', 'ii', 'A', '2']
    assert i5a1iia2.tagged_text == '<E T="03">2.</E> Second info'
    assert i5a1iia2.children == []
    assert i5a1iia3.label == ['737', '5', 'a', 'Interp', '1', 'ii', 'A', '3']
    assert i5a1iia3.tagged_text == '<E T="03">3. Keyterms</E>'
    assert i5a1iia3.children == []


def test_build_supplement_tree_spacing():
    """Integration test"""
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Supplement I to Part 737-Official Interpretations",
               SOURCE='HED')
        ctx.HD("Section 737.5 NASCAR", SOURCE='HD2')
        ctx.child_from_string('<P>1.<E T="03">Phrase</E>. More Content</P>')
        ctx.child_from_string('<P>i. I like<PRTPAGE />ice cream</P>')
        ctx.P("A. Aaaaah")
        ctx.child_from_string('<P><E T="03">1.</E>More info</P>')
    tree = gpo_cfr.build_supplement_tree('737', ctx.xml)
    assert tree.label == ['737', 'Interp']
    assert len(tree.children) == 1

    s5 = tree.children[0]
    assert len(s5.children) == 1

    s51 = s5.children[0]
    assert s51.text == "1. Phrase. More Content"
    assert len(s51.children) == 1

    s51i = s51.children[0]
    assert s51i.text == "i. I like ice cream"
    assert len(s51i.children) == 1

    s51ia = s51i.children[0]
    assert s51ia.text == "A. Aaaaah"
    assert len(s51ia.children) == 1

    s51ia1 = s51ia.children[0]
    assert s51ia1.text == "1. More info"
    assert s51ia1.children == []


def test_build_supplement_tree_repeats():
    """Integration test"""
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Supplement I to Part 737-Official Interpretations",
               SOURCE='HED')
        ctx.HD("Appendices G and H-Content</HD>", SOURCE='HD2')
        ctx.P("1. G:H")
        ctx.HD("Appendix G", SOURCE='HD2')
        ctx.P("1. G")
        ctx.HD("Appendix H", SOURCE='HD2')
        ctx.P("1. H")
    tree = gpo_cfr.build_supplement_tree('737', ctx.xml)
    assert tree.label == ['737', 'Interp']
    assert len(tree.children) == 3
    aGH, aG, aH = tree.children
    assert aGH.label == ['737', 'G_H', 'Interp']
    assert aG.label == ['737', 'G', 'Interp']
    assert aH.label == ['737', 'H', 'Interp']


def test_build_supplement_tree_skip_levels():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Supplement I to Part 737-Official Interpretations",
               SOURCE='HED')
        ctx.HD("Section 737.5 NASCAR", SOURCE='HD2')
        ctx.HD("5(a)(1)(i) Access Device", SOURCE='HD2')
        ctx.P("1. Paragraph 111")
        ctx.HD("5(b) Other Devices", SOURCE='HD2')
        ctx.P("1. Paragraph 222")
    tree = gpo_cfr.build_supplement_tree('737', ctx.xml)
    assert tree.label == ['737', 'Interp']
    assert len(tree.children) == 1

    i5 = tree.children[0]
    assert i5.label == ['737', '5', 'Interp']
    assert len(i5.children) == 2
    i5a, i5b = i5.children

    assert i5a.label == ['737', '5', 'a', 'Interp']
    assert len(i5a.children) == 1
    i5a1 = i5a.children[0]

    assert i5a1.label == ['737', '5', 'a', '1', 'Interp']
    assert len(i5a1.children) == 1
    i5a1i = i5a1.children[0]

    assert i5a1i.label == ['737', '5', 'a', '1', 'i', 'Interp']
    assert len(i5a1i.children) == 1

    assert i5b.label == ['737', '5', 'b', 'Interp']
    assert len(i5b.children) == 1


def test_build_supplement_tree_appendix_paragraphs():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Supplement I to Part 737-Official Interpretations",
               SOURCE='HED')
        ctx.HD("Appendix H", SOURCE='HD2')
        ctx.HD("(b) bbbbbbb", SOURCE='HD3')
        ctx.P("1. Paragraph b")
        ctx.HD("(b)(5) b5b5b5", SOURCE='HD3')
        ctx.P("1. Paragraph b5")
    tree = gpo_cfr.build_supplement_tree('737', ctx.xml)
    assert tree.label == ['737', 'Interp']
    assert len(tree.children) == 1

    ih = tree.children[0]
    assert ih.label == ['737', 'H', 'Interp']
    assert len(ih.children) == 1

    ihb = ih.children[0]
    assert ihb.label == ['737', 'H', 'b', 'Interp']
    assert len(ihb.children) == 2

    ihb1, ihb5 = ihb.children
    assert ihb1.label == ['737', 'H', 'b', 'Interp', '1']
    assert ihb5.label == ['737', 'H', 'b', '5', 'Interp']


def test_build_supplement_intro_section():
    """Integration test"""
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Supplement I to Part 737-Official Interpretations",
               SOURCE='HED')
        ctx.HD("Introduction", SOURCE='HD1')
        ctx.P("1. Some content. (a) Badly named")
        ctx.P("(b) Badly named")
        ctx.HD("Subpart A", SOURCE='HD1')
        ctx.HD("Section 737.13", SOURCE='HD2')
        ctx.child_from_string("<P><E>13(a) Some Stuff!</E></P>")
        ctx.P("1. 131313")
        ctx.HD("Appendix G", SOURCE='HD2')
        ctx.P("1. G")
    tree = gpo_cfr.build_supplement_tree('737', ctx.xml)
    assert tree.label == ['737', 'Interp']
    assert len(tree.children) == 3
    h1, s13, g = tree.children

    assert h1.label == ['737', 'Interp', 'h1']
    assert s13.label == ['737', '13', 'Interp']
    assert g.label == ['737', 'G', 'Interp']

    assert len(h1.children) == 1
    assert h1.children[0].text == ('1. Some content. (a) Badly named\n\n'
                                   '(b) Badly named')
    assert h1.children[0].children == []

    assert len(s13.children) == 1
    assert s13.children[0].title == '13(a) Some Stuff!'


def test_process_inner_child():
    with XMLBuilder('ROOT') as ctx:
        ctx.HD("Title")
        ctx.P("1. 111. i. iii")
        ctx.STARS()
        ctx.P("A. AAA")
        ctx.child_from_string('<P><E T="03">1.</E> eee</P>')
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    n1 = stack.m_stack[0][0][1]
    assert n1.label == ['1']
    assert len(n1.children) == 1

    n1i = n1.children[0]
    assert n1i.label == ['1', 'i']
    assert n1i.text == 'i. iii'
    assert len(n1i.children) == 1

    n1ia = n1i.children[0]
    assert n1ia.label == ['1', 'i', 'A']
    assert len(n1ia.children) == 1

    n1ia1 = n1ia.children[0]
    assert n1ia1.label == ['1', 'i', 'A', '1']
    assert n1ia1.children == []


def test_process_inner_child_space():
    with XMLBuilder('ROOT') as ctx:
        ctx.HD("Title")
        ctx.P("1. 111")
        ctx.P("i. See country A. Not that country")
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    n1 = stack.m_stack[0][0][1]
    assert n1.label == ['1']
    assert len(n1.children) == 1

    n1i = n1.children[0]
    assert n1i.label == ['1', 'i']
    assert n1i.children == []


def test_process_inner_child_incorrect_xml():
    with XMLBuilder('ROOT') as ctx:
        ctx.HD("Title")
        ctx.child_from_string('<P><E T="03">1.</E> 111</P>')
        ctx.P("i. iii")
        ctx.child_from_string('<P><E T="03">2.</E> 222 Incorrect Content</P>')
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    assert len(stack.m_stack[0]) == 2


def test_process_inner_child_no_marker():
    with XMLBuilder() as ctx:
        ctx.HD("Title")
        ctx.P("1. 111")
        ctx.P("i. iii")
        ctx.P("Howdy Howdy")
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    i1 = stack.m_stack[0][0][1]
    assert len(i1.children) == 1
    i1i = i1.children[0]
    assert i1i.children == []
    assert i1i.text == "i. iii\n\nHowdy Howdy"


def test_process_inner_child_has_citation():
    with XMLBuilder() as ctx:
        ctx.HD("Title")
        ctx.P("1. Something something see comment 22(a)-2.i. please")
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    tree = stack.m_stack[0][0][1]
    assert tree.children == []


def test_process_inner_child_stars_and_inline():
    with XMLBuilder() as ctx:
        ctx.HD("Title")
        ctx.STARS()
        ctx.P("2. Content. * * *")
        ctx.STARS()
        ctx.P("xi. Content")
        ctx.STARS()
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    tree = stack.m_stack[0][0][1]
    assert tree.label == ['2']
    assert len(tree.children) == 1
    assert tree.children[0].label == ['2', 'xi']
    assert tree.children[0].children == []


def test_process_inner_child_collapsed_i():
    with XMLBuilder() as ctx:
        ctx.HD("Title")
        ctx.child_from_string(
            '<P>1. <E T="03">Keyterm text</E> i. Content content</P>')
        ctx.P("ii. Other stuff")
    node = ctx.xml.xpath('//HD')[0]
    stack = tree_utils.NodeStack()
    gpo_cfr.process_inner_children(stack, node)
    while stack.size() > 1:
        stack.unwind()
    tree = stack.m_stack[0][0][1]
    assert tree.label == ['1']
    assert len(tree.children) == 2
    assert tree.children[0].label == ['1', 'i']
    assert tree.children[0].children == []
    assert tree.children[1].label == ['1', 'ii']
    assert tree.children[1].children == []


@pytest.mark.parametrize('title', [
    "<HD SOURCE='HD1'>Some Title</HD>",
    "<HD SOURCE='HD2'>Some Title</HD>",
    "<P><E T='03'>Section 111.22</E></P>",
    "<P><E T='03'>21(b) Contents</E>.</P>",
    "<P>31(r) Contents.</P>",
    "<P>Section 111.31 Contents.</P>",
    "<P>Paragraph 51(b)(1)(i).</P>",
])
def test_is_title_success(title):
    assert gpo_cfr.is_title(etree.fromstring(title))


@pytest.mark.parametrize('title', [
    "<HD SOURCE='HED'>Some Header</HD>",
    "<IMG>Some Image</IMG>",
    "<P>Then Section 22.111</P>",
    "<P><E T='03'>Section 222.33</E> More text</P>",
    "<P><E T='03'>Keyterm.</E> More text</P>",
])
def test_is_title_fail(title):
    assert not gpo_cfr.is_title(etree.fromstring(title))


def test_collapsed_markers_matches():
    assert ['i'] == [m.group(1) for m in gpo_cfr.collapsed_markers_matches(
                     '1. AAA - i. More', '1. AAA - i. More')]
    assert ['1'] == [m.group(1) for m in gpo_cfr.collapsed_markers_matches(
                     'A. AAA: 1. More', 'A. AAA: <E T="03">1</E>. More')]
    for txt in ("1. Content - i.e. More content",
                "1. Stuff in quotes like, “N.A.”",
                "i. References appendix D, part I.A.1. Stuff"
                "A. AAA - 1. More, without tags"):
        assert gpo_cfr.collapsed_markers_matches(txt, txt) == []
