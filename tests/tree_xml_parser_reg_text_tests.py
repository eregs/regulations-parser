# vim: set encoding=utf-8
from unittest import TestCase

from lxml import etree
from mock import patch

from regparser.tree.depth import markers as mtypes
from regparser.tree.xml_parser import reg_text
from tests.xml_builder import LXMLBuilder


class RegTextTest(TestCase):
    def setUp(self):
        self.tree = LXMLBuilder()

    def test_build_from_section_intro_text(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P("Some content about this section.")
            root.P("(a) something something")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual('Some content about this section.', node.text.strip())
        self.assertEqual(1, len(node.children))
        self.assertEqual(['8675', '309'], node.label)

        child = node.children[0]
        self.assertEqual('(a) something something', child.text.strip())
        self.assertEqual([], child.children)
        self.assertEqual(['8675', '309', 'a'], child.label)

    def test_build_from_section_collapsed_level(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P(_xml=u"""(a) <E T="03">Transfers </E>—(1)
                           <E T="03">Notice.</E> follow""")
            root.P(_xml="""(b) <E T="03">Contents</E> (1) Here""")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(node.label, ['8675', '309'])
        self.assertEqual(2, len(node.children))
        self.assertEqual(node.children[0].label, ['8675', '309', 'a'])
        self.assertEqual(node.children[1].label, ['8675', '309', 'b'])

        a1_label = node.children[0].children[0].label
        self.assertEqual(['8675', '309', 'a', '1'], a1_label)

        self.assertEqual(1, len(node.children[1].children))

    def test_build_from_section_collapsed_level_emph(self):
        with self.tree.builder('SECTION') as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P("(a) aaaa")
            root.P("(1) 1111")
            root.P("(i) iiii")
            root.P(_xml=u"""(A) AAA—(<E T="03">1</E>) eeee""")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        a1iA = node.children[0].children[0].children[0].children[0]
        self.assertEqual(u"(A) AAA—", a1iA.text)
        self.assertEqual(1, len(a1iA.children))
        self.assertEqual("(1) eeee", a1iA.children[0].text.strip())

    def test_build_from_section_double_collapsed(self):
        with self.tree.builder('SECTION') as root:
            root.SECTNO(u'§ 8675.309')
            root.SUBJECT('Definitions.')
            root.P(_xml=u"""(a) <E T="03">Keyterm</E>—(1)(i) Content""")
            root.P("(ii) Content2")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(['8675', '309'], node.label)
        self.assertEqual(1, len(node.children))

        a = node.children[0]
        self.assertEqual(['8675', '309', 'a'], a.label)
        self.assertEqual(1, len(a.children))

        a1 = a.children[0]
        self.assertEqual(['8675', '309', 'a', '1'], a1.label)
        self.assertEqual(2, len(a1.children))

        a1i, a1ii = a1.children
        self.assertEqual(['8675', '309', 'a', '1', 'i'], a1i.label)
        self.assertEqual(['8675', '309', 'a', '1', 'ii'], a1ii.label)

    def test_build_from_section_reserved(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.RESERVED("[Reserved]")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(node.label, ['8675', '309'])
        self.assertEqual(u'§ 8675.309 [Reserved]', node.title)
        self.assertEqual([], node.children)

    def test_build_from_section_reserved_range(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§§ 8675.309-8675.311")
            root.RESERVED("[Reserved]")
        n309, n310, n311 = reg_text.build_from_section(
            '8675', self.tree.render_xml())
        self.assertEqual(n309.label, ['8675', '309'])
        self.assertEqual(n310.label, ['8675', '310'])
        self.assertEqual(n311.label, ['8675', '311'])
        self.assertEqual(u'§ 8675.309 [Reserved]', n309.title)
        self.assertEqual(u'§ 8675.310 [Reserved]', n310.title)
        self.assertEqual(u'§ 8675.311 [Reserved]', n311.title)

    def _setup_for_ambiguous(self, final_par):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P("(g) Some Content")
            root.P("(h) H Starts")
            root.P("(1) H-1")
            root.P("(2) H-2")
            root.P("(i) Is this 8675-309-h-2-i or 8675-309-i")
            root.P(final_par)
        return reg_text.build_from_section('8675', self.tree.render_xml())[0]

    def test_build_from_section_ambiguous_ii(self):
        n8675_309 = self._setup_for_ambiguous("(ii) A")
        n8675_309_h = n8675_309.children[1]
        n8675_309_h_2 = n8675_309_h.children[1]
        self.assertEqual(2, len(n8675_309.children))
        self.assertEqual(2, len(n8675_309_h.children))
        self.assertEqual(2, len(n8675_309_h_2.children))

    def test_build_from_section_ambiguous_A(self):
        n8675_309 = self._setup_for_ambiguous("(A) B")
        n8675_309_h = n8675_309.children[1]
        n8675_309_h_2 = n8675_309_h.children[1]
        n8675_309_h_2_i = n8675_309_h_2.children[0]
        self.assertEqual(2, len(n8675_309.children))
        self.assertEqual(2, len(n8675_309_h.children))
        self.assertEqual(1, len(n8675_309_h_2.children))
        self.assertEqual(1, len(n8675_309_h_2_i.children))

    def test_build_from_section_ambiguous_1(self):
        n8675_309 = self._setup_for_ambiguous("(1) C")
        self.assertEqual(3, len(n8675_309.children))

    def test_build_from_section_ambiguous_3(self):
        n8675_309 = self._setup_for_ambiguous("(3) D")
        n8675_309_h = n8675_309.children[1]
        n8675_309_h_2 = n8675_309_h.children[1]
        self.assertEqual(2, len(n8675_309.children))
        self.assertEqual(3, len(n8675_309_h.children))
        self.assertEqual(1, len(n8675_309_h_2.children))

    def test_build_from_section_collapsed(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P("(a) aaa")
            root.P("(1) 111")
            root.P(_xml=u"""(2) 222—(i) iii. (A) AAA""")
            root.P("(B) BBB")
        n309 = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(1, len(n309.children))
        n309_a = n309.children[0]
        self.assertEqual(2, len(n309_a.children))
        n309_a_2 = n309_a.children[1]
        self.assertEqual(1, len(n309_a_2.children))
        n309_a_2_i = n309_a_2.children[0]
        self.assertEqual(2, len(n309_a_2_i.children))

    def test_build_from_section_italic_levels(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P("(a) aaa")
            root.P("(1) 111")
            root.P("(i) iii")
            root.P("(A) AAA")
            root.P(_xml="""(<E T="03">1</E>) i1i1i1""")
            root.P(_xml="""\n(<E T="03">2</E>) i2i2i2""")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(1, len(node.children))
        self.assertEqual(node.label, ['8675', '309'])

        node = node.children[0]
        self.assertEqual(node.label, ['8675', '309', 'a'])
        self.assertEqual(1, len(node.children))

        node = node.children[0]
        self.assertEqual(node.label, ['8675', '309', 'a', '1'])
        self.assertEqual(1, len(node.children))

        node = node.children[0]
        self.assertEqual(node.label, ['8675', '309', 'a', '1', 'i'])
        self.assertEqual(1, len(node.children))

        node = node.children[0]
        self.assertEqual(node.label, ['8675', '309', 'a', '1', 'i', 'A'])
        self.assertEqual(2, len(node.children))

        n1, n2 = node.children
        self.assertEqual(n1.label, ['8675', '309', 'a', '1', 'i', 'A', '1'])
        self.assertEqual(n2.label, ['8675', '309', 'a', '1', 'i', 'A', '2'])

    def test_build_from_section_bad_spaces(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.16")
            root.SUBJECT("Subby Sub Sub.")
            root.STARS()
            root.P(_xml="""(b)<E T="03">General.</E>Content Content.""")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(1, len(node.children))
        nb = node.children[0]
        self.assertEqual(nb.text.strip(), "(b) General. Content Content.")

    def test_build_from_section_section_with_nondigits(self):
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309a")
            root.SUBJECT("Definitions.")
            root.P("Intro content here")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]
        self.assertEqual(node.label, ['8675', '309a'])
        self.assertEqual(0, len(node.children))

    def test_build_from_section_table(self):
        """Account for regtext with a table"""
        with self.tree.builder("SECTION") as root:
            root.SECTNO(u"§ 8675.309")
            root.SUBJECT("Definitions.")
            root.P("(a) aaaa")
            with root.GPOTABLE(CDEF="s25,10", COLS=2, OPTS="L2,i1") as table:
                with table.BOXHD() as hd:
                    hd.CHED(H=1)
                    hd.CHED("Header", H=1)
                with table.ROW() as row:
                    row.ENT("Left content", I="01")
                    row.ENT("Right content")
        node = reg_text.build_from_section('8675', self.tree.render_xml())[0]

        a = node.children[0]
        self.assertEqual(1, len(a.children))
        table = a.children[0]
        self.assertEqual(['8675', '309', 'a', 'p1'], table.label)
        self.assertEqual("||Header|\n|---|---|\n|Left content|Right content|",
                         table.text)
        self.assertEqual("GPOTABLE", table.source_xml.tag)

    def test_get_title(self):
        with self.tree.builder("PART") as root:
            root.HD("regulation title")
        title = reg_text.get_title(self.tree.render_xml())
        self.assertEqual(u'regulation title', title)

    def test_get_reg_part(self):
        """Test various formats for the Regulation part to be present in a
        CFR-XML document"""
        xmls = []
        xmls.append(u"<PART><EAR>Pt. 204</EAR></PART>")
        xmls.append(u"<FDSYS><HEADING>PART 204</HEADING></FDSYS>")
        xmls.append(u"<FDSYS><GRANULENUM>204</GRANULENUM></FDSYS>")
        for xml_str in xmls:
            part = reg_text.get_reg_part(etree.fromstring(xml_str))
            self.assertEqual(part, '204')

    def test_get_reg_part_fr_notice_style(self):
        with self.tree.builder("REGTEXT", PART="204") as root:
            root.SECTION("\n")
        part = reg_text.get_reg_part(self.tree.render_xml())
        self.assertEqual(part, '204')

    def test_get_subpart_title(self):
        with self.tree.builder("SUBPART") as root:
            root.HD(u"Subpart A—First subpart")
        subpart_title = reg_text.get_subpart_title(self.tree.render_xml())
        self.assertEqual(subpart_title, u'Subpart A—First subpart')

    def test_get_subpart_title_reserved(self):
        with self.tree.builder("SUBPART") as root:
            root.RESERVED("Subpart J [Reserved]")
        subpart_title = reg_text.get_subpart_title(self.tree.render_xml())
        self.assertEqual(subpart_title, u'Subpart J [Reserved]')

    def test_build_subpart(self):
        with self.tree.builder("SUBPART") as root:
            root.HD(u"Subpart A—First subpart")
            with root.SECTION() as section:
                section.SECTNO(u"§ 8675.309")
                section.SUBJECT("Definitions.")
                section.P("Some content about this section.")
                section.P("(a) something something")
            with root.SECTION() as section:
                section.SECTNO(u"§ 8675.310")
                section.SUBJECT("Definitions.")
                section.P("Some content about this section.")
                section.P("(a) something something")
        subpart = reg_text.build_subpart('8675', self.tree.render_xml())
        self.assertEqual(subpart.node_type, 'subpart')
        self.assertEqual(len(subpart.children), 2)
        self.assertEqual(subpart.label, ['8675', 'Subpart', 'A'])
        child_labels = [c.label for c in subpart.children]
        self.assertEqual([['8675', '309'], ['8675', '310']], child_labels)

    def test_get_markers(self):
        text = u'(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
        markers = reg_text.get_markers(text)
        self.assertEqual(markers, [u'a', u'1'])

    def test_get_markers_and_text(self):
        text = u'(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
        wrap = '<P>%s</P>' % text

        doc = etree.fromstring(wrap)
        markers = reg_text.get_markers(text)
        result = reg_text.get_markers_and_text(doc, markers)

        markers = [r[0] for r in result]
        self.assertEqual(markers, [u'a', u'1'])

        text = [r[1][0] for r in result]
        self.assertEqual(text, [u'(a) Transfer —', u'(1) Notice. follow'])

        tagged = [r[1][1] for r in result]
        self.assertEqual(
            tagged,
            [u'(a) <E T="03">Transfer </E>—',
             u'(1) <E T="03">Notice.</E> follow'])

    def test_get_markers_and_text_emph(self):
        text = '(A) aaaa. (<E T="03">1</E>) 1111'
        xml = etree.fromstring('<P>%s</P>' % text)
        markers = reg_text.get_markers(text)
        result = reg_text.get_markers_and_text(xml, markers)

        a, a1 = result
        self.assertEqual(('A', ('(A) aaaa. ', '(A) aaaa. ')), a)
        self.assertEqual(('<E T="03">1</E>', ('(1) 1111',
                                              '(<E T="03">1</E>) 1111')), a1)

    def test_get_markers_and_text_deceptive_single(self):
        """Don't treat a single marker differently than multiple, there might
        be prefix text"""
        node = etree.fromstring('<P>Words then (a) a subparagraph</P>')
        results = reg_text.get_markers_and_text(node, ['a'])
        self.assertEqual(len(results), 2)
        prefix, subpar = results

        self.assertEqual(prefix[0], mtypes.MARKERLESS)
        self.assertEqual(prefix[1][0], 'Words then ')
        self.assertEqual(subpar[0], 'a')
        self.assertEqual(subpar[1][0], '(a) a subparagraph')

    def test_get_markers_bad_citation(self):
        text = '(vi)<E T="03">Keyterm.</E>The information required by '
        text += 'paragraphs (a)(2), (a)(4)(iii), (a)(5), (b) through (d), '
        text += '(f), and (g) with respect to something, (i), (j), (l) '
        text += 'through (p), (q)(1), and (r) with respect to something.'
        self.assertEqual(['vi'], reg_text.get_markers(text))

    @patch('regparser.tree.xml_parser.reg_text.content')
    def test_preprocess_xml(self, content):
        with self.tree.builder("CFRGRANULE") as root:
            with root.PART() as part:
                with part.APPENDIX() as appendix:
                    appendix.TAG("Other Text")
                    with appendix.GPH(DEEP=453, SPAN=2) as gph:
                        gph.GID("ABCD.0123")
        content.Macros.return_value = [
            ("//GID[./text()='ABCD.0123']/..",
             """<HD SOURCE="HD1">Some Title</HD><GPH DEEP="453" SPAN="2">"""
             """<GID>EFGH.0123</GID></GPH>""")]
        orig_xml = self.tree.render_xml()
        reg_text.preprocess_xml(orig_xml)

        self.setUp()
        with self.tree.builder("CFRGRANULE") as root:
            with root.PART() as part:
                with part.APPENDIX() as appendix:
                    appendix.TAG("Other Text")
                    appendix.HD("Some Title", SOURCE="HD1")
                    with appendix.GPH(DEEP=453, SPAN=2) as gph:
                        gph.GID("EFGH.0123")

        self.assertEqual(etree.tostring(orig_xml), self.tree.render_string())

    def test_next_marker_stars(self):
        with self.tree.builder("ROOT") as root:
            root.P("(i) Content")
            root.STARS()
            root.PRTPAGE()
            root.STARS()
            root.P("(xi) More")
        xml = self.tree.render_xml()
        self.assertEqual('xi', reg_text.next_marker(xml.getchildren()[0], []))
