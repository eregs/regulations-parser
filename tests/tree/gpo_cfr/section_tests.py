# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple
from contextlib import contextmanager

import pytest
from lxml import etree
from mock import Mock

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
    xml = etree.fromstring('<ROOT><P>{0}</P><STARS/></ROOT>'.format(text))
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


@contextmanager
def section_ctx(part=8675, section=309, subject="Definitions."):
    """Many tests need a SECTION tag followed by the SECTNO and SUBJECT"""
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§ {0}.{1}".format(part, section))
        ctx.SUBJECT(subject)
        yield ctx


def test_build_from_section_intro_text():
    with section_ctx() as ctx:
        ctx.P("Some content about this section.")
        ctx.P("(a) something something")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.text == 'Some content about this section.'
    assert node.child_labels == ['a']

    assert node['a'].text == '(a) something something'
    assert node['a'].children == []


def test_build_from_section_collapsed_level():
    with section_ctx() as ctx:
        ctx.child_from_string(
            '<P>(a) <E T="03">Transfers </E>—(1) <E T="03">Notice.</E> '
            'follow</P>')
        ctx.P("(2) More text")
        ctx.child_from_string('<P>(b) <E T="03">Contents</E> (1) Here</P>')
        ctx.P("(2) More text")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.child_labels == ['a', 'b']
    assert node['a'].child_labels == ['1', '2']
    assert node['b'].child_labels == ['1', '2']


def test_build_from_section_collapsed_level_emph():
    with section_ctx() as ctx:
        ctx.P("(a) aaaa")
        ctx.P("(1) 1111")
        ctx.P("(i) iiii")
        ctx.child_from_string('<P>(A) AAA—(<E T="03">1</E>) eeee</P>')
        ctx.STARS()
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    a1ia = node['a']['1']['i']['A']
    assert a1ia.text == "(A) AAA—"
    assert a1ia.child_labels == ['1']
    assert a1ia['1'].text == "(1) eeee"


def test_build_from_section_double_collapsed():
    with section_ctx() as ctx:
        ctx.child_from_string(
            '<P>(a) <E T="03">Keyterm</E>—(1)(i) Content</P>')
        ctx.P("(ii) Content2")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.child_labels == ['a']
    assert node['a'].child_labels == ['1']
    assert node['a']['1'].child_labels == ['i', 'ii']


def test_build_from_section_reserved():
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§ 8675.309")
        ctx.RESERVED("[Reserved]")
    node = section.build_from_section('8675', ctx.xml)[0]
    assert node.label == ['8675', '309']
    assert node.title == '§ 8675.309 [Reserved]'
    assert node.children == []


def test_build_from_3_section_reserved_range():
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§§ 8675.309-8675.311")
        ctx.RESERVED("[Reserved]")
    n309, n310, n311 = section.build_from_section('8675', ctx.xml)
    assert n309.label == ['8675', '309']
    assert n310.label == ['8675', '310']
    assert n311.label == ['8675', '311']
    assert n309.title == '§ 8675.309 [Reserved]'
    assert n310.title == '§ 8675.310 [Reserved]'
    assert n311.title == '§ 8675.311 [Reserved]'


def test_build_from_4_section_reserved_range():
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§§ 8675.309-8675.312")
        ctx.RESERVED("[Reserved]")
    n309 = section.build_from_section('8675', ctx.xml)[0]
    assert n309.label == ['8675', '309']
    assert n309.title == '§§ 8675.309-312 [Reserved]'


def _setup_for_ambiguous(final_par):
    with section_ctx() as ctx:
        ctx.P("(g) Some Content")
        ctx.P("(h) H Starts")
        ctx.P("(1) H-1")
        ctx.P("(2) H-2")
        ctx.P("(i) Is this 8675-309-h-2-i or 8675-309-i")
        ctx.P(final_par)
    node = section.build_from_section('8675', ctx.xml)[0]
    return NodeAccessor(node)


def test_build_from_section_ambiguous_ii():
    n8675_309 = _setup_for_ambiguous("(ii) A")
    assert n8675_309.child_labels == ['g', 'h']
    assert n8675_309['h'].child_labels == ['1', '2']
    assert n8675_309['h']['2'].child_labels == ['i', 'ii']


def test_build_from_section_ambiguous_a():
    n8675_309 = _setup_for_ambiguous("(A) B")
    assert n8675_309.child_labels == ['g', 'h']
    assert n8675_309['h'].child_labels == ['1', '2']
    assert n8675_309['h']['2'].child_labels == ['i']
    assert n8675_309['h']['2']['i'].child_labels == ['A']


def test_build_from_section_ambiguous_1():
    n8675_309 = _setup_for_ambiguous("(1) C")
    assert n8675_309.child_labels == ['g', 'h', 'i']


def test_build_from_section_ambiguous_3():
    n8675_309 = _setup_for_ambiguous("(3) D")
    assert n8675_309.child_labels == ['g', 'h']
    assert n8675_309['h'].child_labels == ['1', '2', '3']
    assert n8675_309['h']['2'].child_labels == ['i']


def test_build_from_section_collapsed():
    with section_ctx() as ctx:
        ctx.P("(a) aaa")
        ctx.P("(1) 111")
        ctx.child_from_string('<P>(2) 222—(i) iii. (A) AAA</P>')
        ctx.P("(B) BBB")
    n309 = section.build_from_section('8675', ctx.xml)[0]
    n309 = NodeAccessor(n309)
    assert n309.child_labels == ['a']
    assert n309['a'].child_labels == ['1', '2']
    assert n309['a']['2'].child_labels == ['i']
    assert n309['a']['2']['i'].child_labels == ['A', 'B']


def test_build_from_section_italic_levels():
    with section_ctx() as ctx:
        ctx.P("(a) aaa")
        ctx.P("(1) 111")
        ctx.P("(i) iii")
        ctx.P("(A) AAA")
        ctx.child_from_string('<P>(<E T="03">1</E>) i1i1i1</P>')
        ctx.child_from_string('<P>\n(<E T="03">2</E>) i2i2i2</P>')
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.child_labels == ['a']
    assert node['a'].child_labels == ['1']
    assert node['a']['1'].child_labels == ['i']
    assert node['a']['1']['i'].child_labels == ['A']
    assert node['a']['1']['i']['A'].child_labels == ['1', '2']


def test_build_from_section_bad_spaces():
    with section_ctx(section=16) as ctx:
        ctx.STARS()
        ctx.child_from_string(
            '<P>(b)<E T="03">General.</E>Content Content.</P>')
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.label == ['8675', '16']
    assert node.child_labels == ['b']
    assert node['b'].text == "(b) General. Content Content."


def test_build_from_section_section_with_nondigits():
    with section_ctx(section="309a") as ctx:
        ctx.P("Intro content here")
    node = section.build_from_section('8675', ctx.xml)[0]
    assert node.label == ['8675', '309a']
    assert node.children == []


def test_build_from_section_fp():
    with section_ctx() as ctx:
        ctx.P("(a) aaa")
        ctx.P("(b) bbb")
        ctx.FP("fpfpfp")
        ctx.P("(c) ccc")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.child_labels == ['a', 'b', 'c']
    assert node['a'].child_labels == []
    assert node['b'].child_labels == ['p1']
    assert node['b']['p1'].child_labels == []
    assert node['c'].child_labels == []


def test_build_from_section_table():
    """Account for regtext with a table"""
    with section_ctx() as ctx:
        ctx.P("(a) aaaa")
        with ctx.GPOTABLE(CDEF="s25,10", COLS=2, OPTS="L2,i1"):
            with ctx.BOXHD():
                ctx.CHED(H=1)
                ctx.CHED("Header", H=1)
            with ctx.ROW():
                ctx.ENT("Left content", I="01")
                ctx.ENT("Right content")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.child_labels == ['a']
    assert node['a'].child_labels == ['p1']
    assert node['a']['p1'].text == (
        "||Header|\n|---|---|\n|Left content|Right content|")
    assert node['a']['p1'].source_xml.tag == 'GPOTABLE'


def _add_table(ctx):
    with ctx.GPOTABLE(CDEF="6.1,6.1,5.2,5.2,5.2", COLS=5, OPTS="L2"):
        with ctx.BOXHD():
            ctx.CHED("Pounds", H=1)
            ctx.CHED("Over", H=2)
            ctx.CHED("Not over", H=2)
            ctx.CHED("From inhabited building distance (feet)", H=1)
            ctx.CHED("From public railroad and highway distance (feet)", H=1)
            ctx.CHED("From above ground magazine (feet)", H=1)
        with ctx.ROW():
            ctx.ENT("0", I="01")
            ctx.ENT("1,000")
            ctx.ENT("75")
            ctx.ENT("75")
            ctx.ENT("50")
        with ctx.ROW():
            ctx.ENT("1,000", I="01")
            ctx.ENT("5,000")
            ctx.ENT("115")
            ctx.ENT("115")
            ctx.ENT("75")


def test_build_from_section_extract_with_table():
    """Account for regtext with a table in an extract"""
    subject = "Table of distances for storage of low explosives."
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§ 555.219")
        ctx.SUBJECT(subject)
        with ctx.EXTRACT():
            _add_table(ctx)

    node = section.build_from_section('555', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.title == '§ 555.219 ' + subject
    assert node.node_type == 'regtext'
    assert node.label == ['555', '219']
    assert node.child_labels == ['p1']
    assert node['p1'].node_type == 'extract'
    assert node['p1'].child_labels == ['p1']
    assert node['p1']['p1'].node_type == 'regtext'
    assert node['p1']['p1'].source_xml.tag == 'GPOTABLE'
    assert node['p1']['p1'].tagged_text.startswith('<GPOTABLE')


def test_build_from_section_extract_with_table_and_headers():
    """Account for regtext with a header and a table in an extract"""
    subject = 'Table of distances for storage of low explosives.'
    table_first_header_text = (
        "Table: Department of Defense Ammunition and Explosives Standards, "
        "Table 5-4.1 Extract; 4145.27 M, March 1969"
    )
    table_second_header_text = (
        "Table: National Fire Protection Association (NFPA) Official "
        "Standard No. 492, 1968"
    )
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§ 555.219")
        ctx.SUBJECT(subject)
        with ctx.EXTRACT():
            ctx.HD(table_first_header_text, SOURCE='HD1')
            _add_table(ctx)
            ctx.HD(table_second_header_text, SOURCE='HD1')
    node = section.build_from_section('555', ctx.xml)[0]
    node = NodeAccessor(node)
    assert node.title == '§ 555.219 ' + subject
    assert node.node_type == 'regtext'
    assert node.label == ['555', '219']
    assert node.child_labels == ['p1']

    assert node['p1'].node_type == 'extract'
    assert node['p1'].child_labels == ['p1', 'p2', 'p3']

    assert node['p1']['p1'].node_type == 'regtext'
    assert node['p1']['p1'].text == ''
    assert node['p1']['p1'].title == table_first_header_text
    assert node['p1']['p1'].children == []

    assert node['p1']['p2'].node_type == 'regtext'
    assert node['p1']['p2'].source_xml.tag == 'GPOTABLE'
    assert node['p1']['p2'].children == []

    assert node['p1']['p3'].node_type == 'regtext'
    assert node['p1']['p3'].text == ''
    assert node['p1']['p3'].title == table_second_header_text
    assert node['p1']['p3'].children == []


def test_build_from_section_extract():
    """Account for paragraphs within an EXTRACT tag"""
    with section_ctx() as ctx:
        ctx.P("(a) aaaa")
        with ctx.EXTRACT():
            ctx.P("1. Some content")
            ctx.P("2. Other content")
            ctx.P("(3) This paragraph has parens for some reason")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)

    assert node.label == ['8675', '309']
    assert node.child_labels == ['a']
    assert node.text == ''
    assert node.node_type == 'regtext'

    assert node['a'].text == '(a) aaaa'
    assert node['a'].node_type == 'regtext'
    assert node['a'].child_labels == ['p1']

    assert node['a']['p1'].text == ''
    assert node['a']['p1'].node_type == 'extract'
    assert node['a']['p1'].child_labels == ['p1', 'p2', 'p3']

    for child in node['a']['p1'].children:
        assert child.node_type == 'regtext'
    assert node['a']['p1']['p1'].text == "1. Some content"
    assert node['a']['p1']['p2'].text == "2. Other content"
    assert node['a']['p1']['p3'].text == (
        "(3) This paragraph has parens for some reason")


def test_build_from_section_example():
    """Account for paragraphs within an EXAMPLE tag"""
    with section_ctx() as ctx:
        ctx.P("(a) aaaa")
        with ctx.EXAMPLE():
            ctx.P("You need a form if:")
            ctx.P("1. Some content")
            ctx.P("2. Other content")
        with ctx.EXAMPLE():
            ctx.P("You do not need a form if:")
            ctx.P("1. Some content")
            ctx.P("2. Other content")
    node = section.build_from_section('8675', ctx.xml)[0]
    node = NodeAccessor(node)

    assert node.child_labels == ['a']
    assert node['a'].text == '(a) aaaa'
    assert node['a'].child_labels == ['p1', 'p2']

    assert node['a']['p1'].text == ''
    assert node['a']['p1'].child_labels == ['p1', 'p2', 'p3']
    assert node['a']['p1']['p1'].text == 'You need a form if:'
    assert node['a']['p1']['p2'].text == '1. Some content'
    assert node['a']['p1']['p3'].text == '2. Other content'

    assert node['a']['p2'].text == ''
    assert node['a']['p2'].child_labels == ['p1', 'p2', 'p3']
    assert node['a']['p2']['p1'].text == 'You do not need a form if:'
    assert node['a']['p2']['p2'].text == '1. Some content'
    assert node['a']['p2']['p3'].text == '2. Other content'


def test_build_from_section_notes():
    """Account for paragraphs within a NOTES tag"""
    with section_ctx() as ctx:
        ctx.P("(a) aaaa")
        with ctx.NOTES():
            ctx.PRTPAGE(P="8")
            ctx.P("1. Some content")
            ctx.P("2. Other content")
    node = NodeAccessor(section.build_from_section('8675', ctx.xml)[0])
    assert node.child_labels == ['a']
    assert node['a'].child_labels == ['p1']
    assert node['a']['p1'].node_type == Node.NOTE
    assert node['a']['p1'].child_labels == ['1', '2']


def test_build_from_section_whitespace():
    """The whitespace in the section text (and intro paragraph) should get
    removed"""
    with XMLBuilder("SECTION", "\n\n") as ctx:
        ctx.SECTNO("§ 8675.309")
        ctx.SUBJECT("subsubsub")
        ctx.P("   Some \n content\n")
        ctx.P("(a) aaa")
        ctx.P("(b) bbb")

    node = section.build_from_section('8675', ctx.xml)[0]
    assert node.text == "Some \n content"


def test_build_from_section_image():
    """We should process images (GPH/GID)"""
    with XMLBuilder("SECTION", "\n\n") as ctx:
        ctx.SECTNO("§ 8675.309")
        ctx.SUBJECT("subsubsub")
        ctx.P("(a) aaa")
        with ctx.GPH():
            ctx.GID("a-gid")
        ctx.P("(b) bbb")

    node = NodeAccessor(section.build_from_section('8675', ctx.xml)[0])
    assert node.child_labels == ['a', 'b']
    assert node['a'].child_labels == ['p1']
    assert node['a']['p1'].text == '![](a-gid)'


def test_build_from_section_double_alpha():
    # Ensure we match a hierarchy like (x), (y), (z), (aa), (bb)…
    with XMLBuilder("SECTION") as ctx:
        ctx.SECTNO("§ 8675.309")
        ctx.SUBJECT("Definitions.")
        ctx.P("(aa) This is what things mean:")
    node = section.build_from_section('8675', ctx.xml)[0]
    child = node.children[0]
    assert child.text == '(aa) This is what things mean:'
    assert child.label == ['8675', '309', 'aa']


def test_parse_empty_part(monkeypatch):
    """Verify that ParseEmptyPart creates the empty part if no children are
    present, but then appends to the last child"""
    monkeypatch.setattr(section, 'build_from_section',
                        Mock(side_effect=[['A', 'B'], ['C']]))
    root = Node(label=['111'])
    assert root.children == []

    section.ParseEmptyPart()(root, Mock())
    assert len(root.children) == 1
    assert root.children[0].label == ['111', 'Subpart']
    assert root.children[0].children == ['A', 'B']   # Not realistic

    section.ParseEmptyPart()(root, Mock())
    assert len(root.children) == 1
    assert root.children[0].label == ['111', 'Subpart']
    assert root.children[0].children == ['A', 'B', 'C']   # Not realistic
