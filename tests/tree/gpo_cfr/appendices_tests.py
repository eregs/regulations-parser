# -*- coding: utf-8 -*-
import pytest

from regparser.test_utils.node_accessor import NodeAccessor
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.gpo_cfr import appendices
from regparser.tree.struct import Node


def test_process_appendix():
    """Integration test for appendices"""
    with XMLBuilder("APPENDIX") as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.P("Intro text")
        ctx.HD("Header 1", SOURCE="HD1")
        ctx.P("Content H1-1")
        ctx.P("Content H1-2")
        ctx.HD("Subheader", SOURCE="HD2")
        ctx.P("Subheader content")
        with ctx.HD("Header ", SOURCE="HD1"):
            ctx.E("2", T="03")
        ctx.P("www.example.com")
        with ctx.P("Final "):
            ctx.E("Content", T="03")
        with ctx.GPH():
            ctx.PRTPAGE(P="650")
            ctx.GID("MYGID")
        with ctx.GPOTABLE(CDEF="s50,15,15", COLS="3", OPTS="L2"):
            with ctx.BOXHD():
                with ctx.CHED("For some reason", H="1"):
                    ctx.LI("lis")
                ctx.CHED("column two", H="2")
                ctx.CHED("a third column", H="2")
            with ctx.ROW():
                ctx.ENT("0", I="01")
                ctx.ENT()
                ctx.ENT("Content3")
            with ctx.ROW():
                ctx.ENT("Cell 1")
                ctx.ENT("Cell 2")
                ctx.ENT("Cell 3")
        ctx.FP("A-3 Some header here", SOURCE="FR-1")
        ctx.P("Content A-3")
        ctx.P("A-4 Another header")
        ctx.P("Content A-4")

    appendix = appendices.process_appendix(ctx.xml, 1111)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['p1', 'h1', 'h3', '3', '4']

    assert appendix['p1'].children == []
    assert appendix['p1'].text == "Intro text"

    assert appendix['h1'].child_labels == ['p2', 'p3', 'h2']
    assert appendix['h1'].title == 'Header 1'
    assert appendix['h1']['p2'].children == []
    assert appendix['h1']['p2'].text == 'Content H1-1'
    assert appendix['h1']['p3'].children == []
    assert appendix['h1']['p3'].text == 'Content H1-2'
    assert appendix['h1']['h2'].child_labels == ['p4']
    assert appendix['h1']['h2'].title == 'Subheader'
    assert appendix['h1']['h2']['p4'].text == 'Subheader content'

    assert appendix['h3'].child_labels == ['p5', 'p6', 'p7', 'p8']
    assert appendix['h3'].title == 'Header 2'
    assert appendix['h3']['p5'].text == 'www.example.com'
    assert appendix['h3']['p6'].text == 'Final Content'
    assert appendix['h3']['p7'].text == '![](MYGID)'
    table_lines = appendix['h3']['p8'].text.split('\n')
    assert table_lines[0] == '|For some reason lis|column two|a third column|'
    assert table_lines[1] == '|---|---|---|'
    assert table_lines[2] == '|0||Content3|'
    assert table_lines[3] == '|Cell 1|Cell 2|Cell 3|'

    assert appendix['3'].title == 'A-3 Some header here'
    assert appendix['4'].title == 'A-4 Another header'


def test_process_appendix_fp_dash():
    with XMLBuilder("APPENDIX") as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.FP("FP-DASH filled out with dashes", SOURCE="FP-DASH")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    assert len(appendix.children) == 1
    fp_dash = appendix.children[0]

    assert fp_dash.text.strip() == 'FP-DASH filled out with dashes_____'


def test_process_appendix_header_depth():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        ctx.P("1. Some content")
        ctx.HD("An Interruption", SOURCE='HD3')
        ctx.P("Moo")
        ctx.P("2. More content")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    appendix = NodeAccessor(appendix)
    assert appendix.label == ['1111', 'A']
    assert appendix.child_labels == ['1', '2']

    assert appendix['1'].child_labels == ['h1']
    assert appendix['1'].text == '1. Some content'

    assert appendix['2'].children == []
    assert appendix['2'].text == '2. More content'


def test_process_appendix_header_is_paragraph():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        ctx.HD("A-1 - First kind of awesome", SOURCE='HD2')
        ctx.HD("(A) First Subkind", SOURCE='HD3')
        ctx.P("1. Content")
        ctx.HD("(B) Next Subkind", SOURCE='HD3')
        ctx.P("1. Moar Contents")
        ctx.HD("I. Remains Header", SOURCE='HD3')
        ctx.P("1. Content tent")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    appendix = NodeAccessor(appendix)
    assert appendix.label == ['1111', 'A']
    assert appendix.child_labels == ['1']

    assert appendix['1'].child_labels == ['A', 'B']
    assert appendix['1'].title == 'A-1 - First kind of awesome'
    assert appendix['1']['A'].child_labels == ['1']
    assert appendix['1']['A'].text == '(A) First Subkind'
    assert appendix['1']['A']['1'].text == '1. Content'
    assert appendix['1']['B'].child_labels == ['1']
    assert appendix['1']['B'].text == '(B) Next Subkind'
    assert appendix['1']['B']['1'].text == '1. Moar Contents'
    assert appendix['1']['B']['1'].child_labels == ['h1']
    assert appendix['1']['B']['1']['h1'].title == 'I. Remains Header'
    assert appendix['1']['B']['1']['h1'].child_labels == ['1']
    assert appendix['1']['B']['1']['h1']['1'].text == '1. Content tent'


def test_process_spaces():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        ctx.child_from_string('<P>1. For<PRTPAGE P="650" />example</P>')
        with ctx.P("2. And "):
            ctx.E("et seq.", T="03")
        with ctx.P("3. And"):
            ctx.E("et seq.", T="03")
        ctx.child_from_string('<P>More<PRTPAGE P="651" />content</P>')
        with ctx.P("And"):
            ctx.E("et seq.", T="03")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['1', '2', '3', 'p1', 'p2']
    for child in appendix.children:
        assert child.children == []
    assert appendix['1'].text == '1. For example'
    assert appendix['2'].text == '2. And et seq.'
    assert appendix['3'].text == '3. And et seq.'
    assert appendix['p1'].text == 'More content'
    assert appendix['p2'].text == 'And et seq.'


def test_header_ordering():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        ctx.HD("A-1 Content", SOURCE='HD1')
        ctx.HD("Level 1", SOURCE='HD3')
        ctx.HD("Level 2", SOURCE='HD2')     # Note HD3 then HD2
        ctx.P("Paragraph")
        ctx.HD("A-1(A) More Content", SOURCE='HD1')
        ctx.P("A1A Paragraph")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['1', '1(A)']
    assert appendix['1'].child_labels == ['h1']
    assert appendix['1']['h1'].child_labels == ['h2']
    assert appendix['1']['h1']['h2'].child_labels == ['p1']
    assert appendix['1']['h1']['h2']['p1'].children == []


def test_process_same_sub_level():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        ctx.P("1. 1 1 1")
        ctx.P("a. 1a 1a 1a")
        ctx.P("b. 1b 1b 1b")
        ctx.P("c. 1c 1c 1c")
        ctx.P("d. 1d 1d 1d")
        ctx.P("e. 1e 1e 1e")
        ctx.P("f. 1f 1f 1f")
        ctx.P("2. 2 2 2")
        ctx.P("a. 2a 2a 2a")
        ctx.P("i. 2ai 2ai 2ai")
        ctx.P("ii. 2aii 2aii 2aii")
        ctx.P("a. 2aiia 2aiia 2aiia")
        ctx.P("b. 2aiib 2aiib 2aiib")
        ctx.P("c. 2aiic 2aiic 2aiic")
        ctx.P("d. 2aiid 2aiid 2aiid")
        ctx.P("b. 2b 2b 2b")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['1', '2']
    assert appendix['1'].child_labels == ['a', 'b', 'c', 'd', 'e', 'f']
    assert appendix['2'].child_labels == ['a', 'b']
    assert appendix['2']['a'].child_labels == ['i', 'ii']
    assert appendix['2']['a']['i'].children == []
    assert appendix['2']['a']['ii'].child_labels == ['a', 'b', 'c', 'd']
    assert appendix['2']['b'].children == []


def test_process_notes():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        with ctx.NOTE():
            ctx.P("Par")
            ctx.E("Emem")
            ctx.P("Parparpar")
    appendix = appendices.process_appendix(ctx.xml, 1111)
    assert appendix.label == ['1111', 'A']
    assert len(appendix.children) == 1
    note = appendix.children[0]
    assert note.text == '```note\nPar\nEmem\nParparpar\n```'


def test_process_code():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        with ctx.CODE(LANGUAGE='scala'):
            ctx.P("// Non-tail-recursive list reverse")
            ctx.FP("def rev[A](lst: List[A]):List[A] =", SOUURCE='FP-2')
            ctx.FP("lst match {", SOURCE='FP-2')
            ctx.FP("  case Nil => Nil", SOURCE='FP-2')
            ctx.FP("  case head :: tail =>", SOURCE='FP-2')
            ctx.FP("    rev(tail) ++ List(head)", SOURCE='FP-2')
            ctx.FP("}", SOURCE='FP-2')
    appendix = appendices.process_appendix(ctx.xml, 1111)
    assert appendix.label == ['1111', 'A']
    assert len(appendix.children) == 1
    code = appendix.children[0]
    text = "\n".join(p.text.strip() for p in ctx.xml.xpath("//P | //FP"))
    assert code.text == "```scala\n" + text + "\n```"


@pytest.mark.parametrize('marker,plain', [
    ('i.', 'i'), ('iv.', 'iv'), ('A.', 'A'), ('3.', '3'),
    ('(i)', 'i'), ('(iv)', 'iv'), ('(A)', 'A'), ('(3)', '3'),
])
def test_initial_marker(marker, plain):
    assert appendices.initial_marker(marker + ' Hi') == (plain, marker)


def test_remove_toc1():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.FP("A-1 Awesome")
        ctx.FP("A-2 More Awesome")
        ctx.FP("A-1 Incorrect TOC")
        ctx.P("A-3 The End of Awesome")
        ctx.HD("A-1Awesomer")
        ctx.P("Content content")
    appendices.remove_toc(ctx.xml, 'A')
    assert [t.tag for t in ctx.xml] == ['EAR', 'HD', 'HD', 'P']


def test_remove_toc2():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.FP("A-1 Awesome")
        ctx.FP("A-2 More Awesome")
        ctx.FP("A-1 Incorrect TOC")
        ctx.P("A-3 The End of Awesome")
        with ctx.GPH():
            ctx.GID("GIDGID")
        ctx.HD("A-3Awesomer")
        ctx.P("Content content")
    appendices.remove_toc(ctx.xml, 'A')
    assert [t.tag for t in ctx.xml] == ['EAR', 'HD', 'GPH', 'HD', 'P']


def test_remove_toc3():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.FP("A-1 Awesome")
        ctx.P("Good Content here")
        ctx.FP("A-2 More Awesome")
        ctx.P("More Content")
        ctx.HD("A-11 Crank It Up")
        ctx.P("Content content")
    appendices.remove_toc(ctx.xml, 'A')
    assert [t.tag for t in ctx.xml] == [
        'EAR', 'HD', 'FP', 'P', 'FP', 'P', 'HD', 'P']


def test_title_label_pair():
    title = u'A-1—Model Clauses'
    assert appendices.title_label_pair(title, 'A', '1000') == ('1', 2)

    title = u'Part III—Construction Period'
    assert appendices.title_label_pair(title, 'A', '1000') == ('III', 2)


@pytest.mark.parametrize('title,output', [
    [u'G-13(A)—Has No parent', ('13(A)', 2)],
    [u'G-13(C)(1) - Some Title', ('13(C)(1)', 2)],
    [u'G-13A - Some Title', ('13A', 2)],
    [u'G-13And Some Smashed Text', ('13', 2)],
])
def test_title_label_pair_parens(title, output):
    assert appendices.title_label_pair(title, 'G', '1000') == output


def test_paragraph_no_marker():
    ap = appendices.AppendixProcessor(1111)
    ap.paragraph_no_marker("Paragraph Text")
    ap.end_group()
    lvl, node = ap.m_stack.peek_last()
    assert node.text == 'Paragraph Text'
    assert lvl == 1
    assert node.label == ['p1']

    #   If a header was before the paragraph, increment the level 1
    ap.m_stack.add(1, Node(label=['h1'], title='Some section'))
    ap.paragraph_no_marker("Paragraph Text")
    ap.end_group()
    lvl, node = ap.m_stack.peek_last()
    assert node.text == 'Paragraph Text'
    assert lvl == 2
    assert node.label == ['p2']


def test_paragraph_with_marker():
    ap = appendices.AppendixProcessor(1111)
    for text in ('(a) A paragraph', '(b) A paragraph', '(1) A paragraph',
                 '(2) A paragraph', '(c) A paragraph'):
        ap.paragraph_with_marker(text, text)
    ap.paragraph_no_marker('some text')
    ap.paragraph_with_marker('(d) A paragraph', '(d) A paragraph')
    ap.end_group()

    stack = ap.m_stack.m_stack
    assert len(stack) == 1
    level2 = [el[1] for el in stack[0]]
    assert len(level2) == 5
    a, b, c, other, d = level2
    assert a.label == ['a']
    assert a.children == []
    assert b.label == ['b']
    assert len(b.children) == 2
    assert c.label == ['c']
    assert c.children == []
    assert other.label == ['p1']
    assert other.children == []
    assert d.label == ['d']
    assert d.children == []

    b1, b2 = b.children
    assert b1.label == ['b', '1']
    assert b1.children == []
    assert b2.label == ['b', '2']
    assert b2.children == []


def test_paragraph_period():
    ap = appendices.AppendixProcessor(1111)
    for text in ("1. A paragraph", "(a) A paragraph", "A. A paragraph"):
        ap.paragraph_with_marker(text, text)
    ap.paragraph_no_marker("code . is here")
    ap.end_group()

    stack = ap.m_stack.m_stack
    assert len(stack) == 3
    level2, level3, level4 = [[el[1] for el in lvl] for lvl in stack]

    assert len(level2) == 1
    assert level2[0].label == ['1']
    assert len(level3) == 1
    assert level3[0].label == ['a']
    assert len(level4) == 2
    assert level4[0].label == ['A']
    assert level4[1].label == ['p1']


def test_paragraph_roman():
    ap = appendices.AppendixProcessor(1111)
    for text in ("(1) A paragraph", "(a) A paragraph", "(i) A paragraph",
                 "(ii) A paragraph", "(iii) A paragraph",
                 "(iv) A paragraph", "(v) A paragraph"):
        ap.paragraph_with_marker(text, text)
    ap.end_group()

    stack = ap.m_stack.m_stack
    assert len(stack) == 3
    level2, level3, level4 = [[el[1] for el in lvl] for lvl in stack]

    assert len(level2) == 1
    assert level2[0].label == ['1']
    assert len(level3) == 1
    assert level3[0].label == ['a']
    assert len(level4) == 5
    assert [el.label[0] for el in level4] == ['i', 'ii', 'iii', 'iv', 'v']


def test_split_paragraph_text():
    res = appendices.split_paragraph_text(
        "(a) Paragraph. (1) Next paragraph")
    assert res == ['(a) Paragraph. ', '(1) Next paragraph']

    res = appendices.split_paragraph_text(
        "(a) (Keyterm) (1) Next paragraph")
    assert res == ['(a) (Keyterm) ', '(1) Next paragraph']

    res = appendices.split_paragraph_text("(a) Mentions one (1) comment")
    assert res == ['(a) Mentions one (1) comment']


def test_paragraph_double_depth():
    ap = appendices.AppendixProcessor(1111)
    for text in ("(a) A paragraph", "(1) A paragraph", "(i) A paragraph",
                 "(A) A paragraph", "(a) A paragraph"):
        ap.paragraph_with_marker(text, text)
    ap.end_group()

    stack = ap.m_stack.m_stack
    assert len(stack) == 5
    levels = [[el[1] for el in lvl] for lvl in stack]
    assert len(levels) == 5
    for lvl in levels:
        assert len(lvl) == 1
    level2, level3, level4, level5, level6 = levels

    assert level2[0].label == ['a']
    assert level3[0].label == ['1']
    assert level4[0].label == ['i']
    assert level5[0].label == ['A']
    assert level6[0].label == ['a']


def test_process_part_cap():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.HD("Part I - Stuff", SOURCE="HD1")
        ctx.P("A. Content")
    appendix = appendices.AppendixProcessor(1111).process(ctx.xml)
    assert len(appendix.children) == 1
    ai = appendix.children[0]

    assert len(ai.children) == 1


def test_process_depth_look_forward():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE='HED')
        ctx.P("(a) aaaaa")
        ctx.P("(i) iiiii")
        ctx.P("Text text")
        ctx.P("(ii) ii ii ii")
    appendix = appendices.AppendixProcessor(1111).process(ctx.xml)
    assert len(appendix.children) == 1
    aa = appendix.children[0]

    child_labels = [child.label for child in aa.children]
    assert ['1111', 'A', 'a', 'i'] in child_labels
    assert ['1111', 'A', 'a', 'ii'] in child_labels


def test_process_header_depth():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.HD("Title 1", SOURCE="HD1")
        ctx.P("(1) Content 1")
        ctx.P("(2) Content 2")
        ctx.HD("Title 2", SOURCE="HD1")
        ctx.P("A. Content")
    appendix = appendices.AppendixProcessor(1111).process(ctx.xml)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['h1', 'h2']
    assert appendix['h1'].child_labels == ['1', '2']
    assert appendix['h2'].child_labels == ['A']


def test_process_collapsed():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.HD("Part I - Something", SOURCE="HD1")
        ctx.P(u"(a) Something referencing § 999.2(a)(1). (1) Content")
        ctx.P("(2) Something else")
    appendix = appendices.AppendixProcessor(1111).process(ctx.xml)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['I']
    assert appendix['I'].child_labels == ['a']
    assert appendix['I']['a'].child_labels == ['1', '2']
    assert appendix['I']['a']['1'].text == '(1) Content'
    assert appendix['I']['a']['2'].text == '(2) Something else'


def test_process_collapsed_keyterm():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR("Pt. 1111, App. A")
        ctx.HD("Appendix A to Part 1111-Awesome", SOURCE="HED")
        ctx.child_from_string('<P>(a) <E T="03">Keyterm</E> (1) Content</P>')
    appendix = appendices.AppendixProcessor(1111).process(ctx.xml)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['a']
    assert appendix['a'].child_labels == ['1']
    assert appendix['a']['1'].children == []


def test_process_separated_by_header():
    with XMLBuilder('APPENDIX') as ctx:
        ctx.EAR('Pt. 1111, App. A')
        ctx.HD('Appendix A to Part 1111-Awesome', SOURCE='HED')
        ctx.P('(a) aaaaaa')
        ctx.P('(1) 111111')
        ctx.HD('Random Header', SOURCE='HD1')
        ctx.P('(2) 222222')
        ctx.P('Markerless')
    appendix = appendices.AppendixProcessor(1111).process(ctx.xml)
    appendix = NodeAccessor(appendix)
    assert appendix.child_labels == ['a']
    assert appendix['a'].child_labels == ['1', '2', 'p1']
    assert appendix['a']['1'].child_labels == ['h1']
    assert appendix['a']['2'].children == []
    assert appendix['a']['p1'].children == []
