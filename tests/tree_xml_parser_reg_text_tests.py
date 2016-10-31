# vim: set encoding=utf-8
from contextlib import contextmanager
from unittest import TestCase

from lxml import etree
from mock import patch

from regparser.test_utils.node_accessor import NodeAccessor
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.depth import markers as mtypes
from regparser.tree.struct import Node
from regparser.tree.xml_parser import reg_text


class RegTextTest(TestCase):
    @contextmanager
    def section(self, part=8675, section=309, subject="Definitions."):
        """Many tests need a SECTION tag followed by the SECTNO and SUBJECT"""
        with XMLBuilder("SECTION") as ctx:
            ctx.SECTNO(u"§ {}.{}".format(part, section))
            ctx.SUBJECT(subject)
            yield ctx

    def test_build_from_section_intro_text(self):
        with self.section() as ctx:
            ctx.P("Some content about this section.")
            ctx.P("(a) something something")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual('Some content about this section.', node.text.strip())
        self.assertEqual(['a'], node.child_labels)

        self.assertEqual('(a) something something', node['a'].text.strip())
        self.assertEqual([], node['a'].children)

    def test_build_from_section_collapsed_level(self):
        with self.section() as ctx:
            ctx.child_from_string(
                u'<P>(a) <E T="03">Transfers </E>—(1) <E T="03">Notice.</E> '
                u'follow</P>')
            ctx.P("(2) More text")
            ctx.child_from_string(
                '<P>(b) <E T="03">Contents</E> (1) Here</P>')
            ctx.P("(2) More text")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual(['a', 'b'], node.child_labels)
        self.assertEqual(['1', '2'], node['a'].child_labels)
        self.assertEqual(['1', '2'], node['b'].child_labels)

    def test_build_from_section_collapsed_level_emph(self):
        with self.section() as ctx:
            ctx.P("(a) aaaa")
            ctx.P("(1) 1111")
            ctx.P("(i) iiii")
            ctx.child_from_string(u'<P>(A) AAA—(<E T="03">1</E>) eeee</P>')
            ctx.STARS()
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        a1iA = node['a']['1']['i']['A']
        self.assertEqual(u"(A) AAA—", a1iA.text)
        self.assertEqual(['1'], a1iA.child_labels)
        self.assertEqual("(1) eeee", a1iA['1'].text.strip())

    def test_build_from_section_double_collapsed(self):
        with self.section() as ctx:
            ctx.child_from_string(
                u'<P>(a) <E T="03">Keyterm</E>—(1)(i) Content</P>')
            ctx.P("(ii) Content2")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual(['a'], node.child_labels)
        self.assertEqual(['1'], node['a'].child_labels)
        self.assertEqual(['i', 'ii'], node['a']['1'].child_labels)

    def test_build_from_section_reserved(self):
        with XMLBuilder("SECTION") as ctx:
            ctx.SECTNO(u"§ 8675.309")
            ctx.RESERVED("[Reserved]")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        self.assertEqual(node.label, ['8675', '309'])
        self.assertEqual(u'§ 8675.309 [Reserved]', node.title)
        self.assertEqual([], node.children)

    def test_build_from_3_section_reserved_range(self):
        with XMLBuilder("SECTION") as ctx:
            ctx.SECTNO(u"§§ 8675.309-8675.311")
            ctx.RESERVED("[Reserved]")
        n309, n310, n311 = reg_text.build_from_section('8675', ctx.xml)
        self.assertEqual(n309.label, ['8675', '309'])
        self.assertEqual(n310.label, ['8675', '310'])
        self.assertEqual(n311.label, ['8675', '311'])
        self.assertEqual(u'§ 8675.309 [Reserved]', n309.title)
        self.assertEqual(u'§ 8675.310 [Reserved]', n310.title)
        self.assertEqual(u'§ 8675.311 [Reserved]', n311.title)

    def test_build_from_4_section_reserved_range(self):
        with XMLBuilder("SECTION") as ctx:
            ctx.SECTNO(u"§§ 8675.309-8675.312")
            ctx.RESERVED("[Reserved]")
        n309 = reg_text.build_from_section('8675', ctx.xml)[0]
        self.assertEqual(n309.label, ['8675', '309'])
        self.assertEqual(u'§§ 8675.309-312 [Reserved]', n309.title)

    def _setup_for_ambiguous(self, final_par):
        with self.section() as ctx:
            ctx.P("(g) Some Content")
            ctx.P("(h) H Starts")
            ctx.P("(1) H-1")
            ctx.P("(2) H-2")
            ctx.P("(i) Is this 8675-309-h-2-i or 8675-309-i")
            ctx.P(final_par)
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        return NodeAccessor(node)

    def test_build_from_section_ambiguous_ii(self):
        n8675_309 = self._setup_for_ambiguous("(ii) A")
        self.assertEqual(['g', 'h'], n8675_309.child_labels)
        self.assertEqual(['1', '2'], n8675_309['h'].child_labels)
        self.assertEqual(['i', 'ii'], n8675_309['h']['2'].child_labels)

    def test_build_from_section_ambiguous_A(self):
        n8675_309 = self._setup_for_ambiguous("(A) B")
        self.assertEqual(['g', 'h'], n8675_309.child_labels)
        self.assertEqual(['1', '2'], n8675_309['h'].child_labels)
        self.assertEqual(['i'], n8675_309['h']['2'].child_labels)
        self.assertEqual(['A'], n8675_309['h']['2']['i'].child_labels)

    def test_build_from_section_ambiguous_1(self):
        n8675_309 = self._setup_for_ambiguous("(1) C")
        self.assertEqual(['g', 'h', 'i'], n8675_309.child_labels)

    def test_build_from_section_ambiguous_3(self):
        n8675_309 = self._setup_for_ambiguous("(3) D")
        self.assertEqual(['g', 'h'], n8675_309.child_labels)
        self.assertEqual(['1', '2', '3'], n8675_309['h'].child_labels)
        self.assertEqual(['i'], n8675_309['h']['2'].child_labels)

    def test_build_from_section_collapsed(self):
        with self.section() as ctx:
            ctx.P("(a) aaa")
            ctx.P("(1) 111")
            ctx.child_from_string(u'<P>(2) 222—(i) iii. (A) AAA</P>')
            ctx.P("(B) BBB")
        n309 = reg_text.build_from_section('8675', ctx.xml)[0]
        n309 = NodeAccessor(n309)
        self.assertEqual(['a'], n309.child_labels)
        self.assertEqual(['1', '2'], n309['a'].child_labels)
        self.assertEqual(['i'], n309['a']['2'].child_labels)
        self.assertEqual(['A', 'B'], n309['a']['2']['i'].child_labels)

    def test_build_from_section_italic_levels(self):
        with self.section() as ctx:
            ctx.P("(a) aaa")
            ctx.P("(1) 111")
            ctx.P("(i) iii")
            ctx.P("(A) AAA")
            ctx.child_from_string('<P>(<E T="03">1</E>) i1i1i1</P>')
            ctx.child_from_string('<P>\n(<E T="03">2</E>) i2i2i2</P>')
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual(['a'], node.child_labels)
        self.assertEqual(['1'], node['a'].child_labels)
        self.assertEqual(['i'], node['a']['1'].child_labels)
        self.assertEqual(['A'], node['a']['1']['i'].child_labels)
        self.assertEqual(['1', '2'], node['a']['1']['i']['A'].child_labels)

    def test_build_from_section_bad_spaces(self):
        with self.section(section=16) as ctx:
            ctx.STARS()
            ctx.child_from_string(
                '<P>(b)<E T="03">General.</E>Content Content.</P>')
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual(['8675', '16'], node.label)
        self.assertEqual(['b'], node.child_labels)
        self.assertEqual(node['b'].text.strip(),
                         "(b) General. Content Content.")

    def test_build_from_section_section_with_nondigits(self):
        with self.section(section="309a") as ctx:
            ctx.P("Intro content here")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        self.assertEqual(node.label, ['8675', '309a'])
        self.assertEqual(0, len(node.children))

    def test_build_from_section_fp(self):
        with self.section() as ctx:
            ctx.P("(a) aaa")
            ctx.P("(b) bbb")
            ctx.FP("fpfpfp")
            ctx.P("(c) ccc")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual(['a', 'b', 'c'], node.child_labels)
        self.assertEqual([], node['a'].child_labels)
        self.assertEqual(['p1'], node['b'].child_labels)
        self.assertEqual([], node['b']['p1'].child_labels)
        self.assertEqual([], node['c'].child_labels)

    def test_build_from_section_table(self):
        """Account for regtext with a table"""
        with self.section() as ctx:
            ctx.P("(a) aaaa")
            with ctx.GPOTABLE(CDEF="s25,10", COLS=2, OPTS="L2,i1"):
                with ctx.BOXHD():
                    ctx.CHED(H=1)
                    ctx.CHED("Header", H=1)
                with ctx.ROW():
                    ctx.ENT("Left content", I="01")
                    ctx.ENT("Right content")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        node = NodeAccessor(node)
        self.assertEqual(['a'], node.child_labels)
        self.assertEqual(['p1'], node['a'].child_labels)
        self.assertEqual("||Header|\n|---|---|\n|Left content|Right content|",
                         node['a']['p1'].text)
        self.assertEqual("GPOTABLE", node['a']['p1'].source_xml.tag)

    def test_build_from_section_extract_with_table(self):
        """Account for regtext with a table in an extract"""
        subject = "Table of distances for storage of low explosives."
        railroad = "From public railroad and highway distance (feet)"
        xml = etree.fromstring("""
          <SECTION>
            <SECTNO>§ 555.219</SECTNO>
            <SUBJECT>%s</SUBJECT>
            <EXTRACT>
                <GPOTABLE CDEF="6.1,6.1,5.2,5.2,5.2" COLS="5" OPTS="L2">
                  <BOXHD>
                    <CHED H="1">Pounds</CHED>
                    <CHED H="2">Over</CHED>
                    <CHED H="2">Not over</CHED>
                    <CHED H="1">From inhabited building distance (feet)</CHED>
                    <CHED H="1">%s</CHED>
                    <CHED H="1">From above ground magazine (feet)</CHED>
                  </BOXHD>
                  <ROW>
                    <ENT I="01">0</ENT>
                    <ENT>1,000</ENT>
                    <ENT>75</ENT>
                    <ENT>75</ENT>
                    <ENT>50</ENT>
                  </ROW>
                  <ROW>
                    <ENT I="01">1,000</ENT>
                    <ENT>5,000</ENT>
                    <ENT>115</ENT>
                    <ENT>115</ENT>
                    <ENT>75</ENT>
                  </ROW>
                </GPOTABLE>
            </EXTRACT>
          </SECTION>
        """ % (subject, railroad))

        nodes = reg_text.build_from_section('555', xml)
        node = nodes[0]
        self.assertEqual(u'§ 555.219 %s' % subject, node.title)
        self.assertEqual('regtext', node.node_type)
        self.assertEqual(['555', '219'], node.label)
        self.assertEqual(1, len(node.children))

        extract_node = node.children[0]
        self.assertEqual('extract', extract_node.node_type)
        self.assertEqual(1, len(extract_node.children))

        table_node = extract_node.children[0]
        self.assertEqual('regtext', table_node.node_type)
        self.assertEqual('GPOTABLE', table_node.source_xml.tag)
        self.assertTrue(table_node.tagged_text.startswith('<GPOTABLE'))

    def test_build_from_section_extract_with_table_and_headers(self):
        """Account for regtext with a header and a table in an extract"""
        subject = u'Table of distances for storage of low explosives.'
        table_first_header_text = ''.join([
            'Table: Department of Defense Ammunition and ',
            'Explosives Standards, Table 5-4.1 Extract; ',
            '4145.27 M, March 1969'])
        table_second_header_text = ''.join(['Table: National Fire Protection ',
                                            'Association (NFPA) Official ',
                                            'Standard No. 492, 1968'])
        xml = etree.fromstring(u"""
          <SECTION>
            <SECTNO>§ 555.219</SECTNO>
            <SUBJECT>%s</SUBJECT>
            <EXTRACT>
                <HD SOURCE="HD1">%s</HD>
                <GPOTABLE CDEF="6.1,6.1,5.2,5.2,5.2" COLS="5" OPTS="L2">
                  <BOXHD>
                    <CHED H="1">Pounds</CHED>
                    <CHED H="2">Over</CHED>
                    <CHED H="2">Not over</CHED>
                    <CHED H="1">From inhabited building distance (feet)</CHED>
                    <CHED H="1">From public railroad and highway distance
                        (feet)</CHED>
                    <CHED H="1">From above ground magazine (feet)</CHED>
                  </BOXHD>
                  <ROW>
                    <ENT I="01">0</ENT>
                    <ENT>1,000</ENT>
                    <ENT>75</ENT>
                    <ENT>75</ENT>
                    <ENT>50</ENT>
                  </ROW>
                  <ROW>
                    <ENT I="01">1,000</ENT>
                    <ENT>5,000</ENT>
                    <ENT>115</ENT>
                    <ENT>115</ENT>
                    <ENT>75</ENT>
                  </ROW>
                </GPOTABLE>
                <HD SOURCE="HD1">%s</HD>
            </EXTRACT>
          </SECTION>
        """ % (subject, table_first_header_text, table_second_header_text))
        nodes = reg_text.build_from_section('555', xml)
        node = nodes[0]
        self.assertEqual(u'§ 555.219 %s' % subject, node.title)
        self.assertEqual('regtext', node.node_type)
        self.assertEqual(['555', '219'], node.label)
        self.assertEqual(1, len(node.children))

        extract_node = node.children[0]
        self.assertEqual('extract', extract_node.node_type)
        self.assertEqual(['555', '219', 'p1'], extract_node.label)
        self.assertEqual(3, len(extract_node.children))

        first_header_node = extract_node.children[0]
        self.assertEqual('regtext', first_header_node.node_type)
        self.assertEqual('', first_header_node.text)
        self.assertEqual(table_first_header_text, first_header_node.title)
        self.assertEqual(['555', '219', 'p1', 'p1'], first_header_node.label)
        self.assertEqual(0, len(first_header_node.children))

        table_node = extract_node.children[1]
        self.assertEqual('regtext', table_node.node_type)
        self.assertEqual('GPOTABLE', table_node.source_xml.tag)
        self.assertEqual(['555', '219', 'p1', 'p2'], table_node.label)
        self.assertEqual(0, len(table_node.children))

        second_header_node = extract_node.children[2]
        self.assertEqual('regtext', second_header_node.node_type)
        self.assertEqual('', second_header_node.text)
        self.assertEqual(table_second_header_text, second_header_node.title)
        self.assertEqual(['555', '219', 'p1', 'p3'], second_header_node.label)
        self.assertEqual(0, len(second_header_node.children))

    def test_build_from_section_extract(self):
        """Account for paragraphs within an EXTRACT tag"""
        with self.section() as ctx:
            ctx.P("(a) aaaa")
            with ctx.EXTRACT():
                ctx.P("1. Some content")
                ctx.P("2. Other content")
                ctx.P("(3) This paragraph has parens for some reason")
        nodes = reg_text.build_from_section('8675', ctx.xml)

        root_node = nodes[0]
        self.assertEqual(['8675', '309'], root_node.label)
        self.assertEqual(1, len(root_node.children))
        self.assertEqual('', root_node.text)
        self.assertEqual("regtext", root_node.node_type)

        outer_p_node = root_node.children[0]
        self.assertEqual(['8675', '309', 'a'], outer_p_node.label)
        self.assertEqual(1, len(outer_p_node.children))
        self.assertEqual('(a) aaaa', outer_p_node.text)
        self.assertEqual("regtext", outer_p_node.node_type)

        extract_node = outer_p_node.children[0]
        self.assertEqual(['8675', '309', 'a', 'p1'], extract_node.label)
        self.assertEqual(3, len(extract_node.children))
        self.assertEqual('', extract_node.text)
        self.assertEqual("extract", extract_node.node_type)

        first_p_node, second_p_node, third_p_node = extract_node.children
        self.assertEqual(['8675', '309', 'a', 'p1', 'p1'], first_p_node.label)
        self.assertEqual(['8675', '309', 'a', 'p1', 'p2'], second_p_node.label)
        self.assertEqual(['8675', '309', 'a', 'p1', 'p3'], third_p_node.label)
        self.assertEqual("regtext", first_p_node.node_type,
                         second_p_node.node_type)
        self.assertEqual('1. Some content', first_p_node.text)
        self.assertEqual('2. Other content', second_p_node.text)
        self.assertEqual('(3) This paragraph has parens for some reason',
                         third_p_node.text)

    def test_build_from_section_example(self):
        """Account for paragraphs within an EXAMPLE tag"""
        with self.section() as ctx:
            ctx.P("(a) aaaa")
            with ctx.EXAMPLE():
                ctx.P("You need a form if:")
                ctx.P("1. Some content")
                ctx.P("2. Other content")
            with ctx.EXAMPLE():
                ctx.P("You do not need a form if:")
                ctx.P("1. Some content")
                ctx.P("2. Other content")
        node = reg_text.build_from_section('8675', ctx.xml)[0]

        a = node.children[0]
        self.assertEqual(u'(a) aaaa', a.text)
        self.assertEqual(2, len(a.children))
        self.assertEqual(['8675', '309', 'a'], a.label)

        example_one = a.children[0]
        self.assertEqual(u'', example_one.text)
        self.assertEqual(3, len(example_one.children))
        self.assertEqual(['8675', '309', 'a', 'p1'], example_one.label)

        children = example_one.children
        self.assertEqual(u'You need a form if:', children[0].text)
        self.assertEqual(['8675', '309', 'a', 'p1', 'p1'], children[0].label)
        self.assertEqual(u'1. Some content', children[1].text)
        self.assertEqual(['8675', '309', 'a', 'p1', 'p2'], children[1].label)
        self.assertEqual(u'2. Other content', children[2].text)
        self.assertEqual(['8675', '309', 'a', 'p1', 'p3'], children[2].label)

        example_two = a.children[1]
        self.assertEqual(u'', example_two.text)
        self.assertEqual(3, len(example_two.children))
        self.assertEqual(['8675', '309', 'a', 'p2'], example_two.label)

        children = example_two.children
        self.assertEqual(u'You do not need a form if:', children[0].text)
        self.assertEqual(['8675', '309', 'a', 'p2', 'p1'], children[0].label)
        self.assertEqual(u'1. Some content', children[1].text)
        self.assertEqual(['8675', '309', 'a', 'p2', 'p2'], children[1].label)
        self.assertEqual(u'2. Other content', children[2].text)
        self.assertEqual(['8675', '309', 'a', 'p2', 'p3'], children[2].label)

    def test_build_from_section_notes(self):
        """Account for paragraphs within a NOTES tag"""
        with self.section() as ctx:
            ctx.P("(a) aaaa")
            with ctx.NOTES():
                ctx.PRTPAGE(P="8")
                ctx.P("1. Some content")
                ctx.P("2. Other content")
        node = NodeAccessor(reg_text.build_from_section('8675', ctx.xml)[0])

        self.assertEqual(['a'], node.child_labels)
        self.assertEqual(['p1'], node['a'].child_labels)
        self.assertEqual(Node.NOTE, node['a']['p1'].node_type)
        self.assertEqual(['1', '2'], node['a']['p1'].child_labels)

    def test_build_from_section_whitespace(self):
        """The whitespace in the section text (and intro paragraph) should get
        removed"""
        with XMLBuilder("SECTION", "\n\n") as ctx:
            ctx.SECTNO(u"§ 8675.309")
            ctx.SUBJECT("subsubsub")
            ctx.P("   Some \n content\n")
            ctx.P("(a) aaa")
            ctx.P("(b) bbb")

        node = reg_text.build_from_section('8675', ctx.xml)[0]
        self.assertEqual(node.text, "Some \n content")

    def test_build_from_section_image(self):
        """We should process images (GPH/GID)"""
        with XMLBuilder("SECTION", "\n\n") as ctx:
            ctx.SECTNO(u"§ 8675.309")
            ctx.SUBJECT("subsubsub")
            ctx.P("(a) aaa")
            with ctx.GPH():
                ctx.GID("a-gid")
            ctx.P("(b) bbb")

        node = NodeAccessor(reg_text.build_from_section('8675', ctx.xml)[0])
        self.assertEqual(['a', 'b'], node.child_labels)
        self.assertEqual(['p1'], node['a'].child_labels)
        self.assertEqual('![](a-gid)', node['a']['p1'].text)

    def test_get_title(self):
        with XMLBuilder("PART") as ctx:
            ctx.HD("regulation title")
        title = reg_text.get_title(ctx.xml)
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
        with XMLBuilder("REGTEXT", PART=204) as ctx:
            ctx.SECTION("\n")
        part = reg_text.get_reg_part(ctx.xml)
        self.assertEqual(part, '204')

    def test_build_subpart(self):
        with XMLBuilder("SUBPART") as ctx:
            ctx.HD(u"Subpart A—First subpart")
            with ctx.SECTION():
                ctx.SECTNO(u"§ 8675.309")
                ctx.SUBJECT("Definitions.")
                ctx.P("Some content about this section.")
                ctx.P("(a) something something")
            with ctx.SECTION():
                ctx.SECTNO(u"§ 8675.310")
                ctx.SUBJECT("Definitions.")
                ctx.P("Some content about this section.")
                ctx.P("(a) something something")
        subpart = reg_text.build_subpart('8675', ctx.xml)
        self.assertEqual(subpart.node_type, 'subpart')
        self.assertEqual(len(subpart.children), 2)
        self.assertEqual(subpart.label, ['8675', 'Subpart', 'A'])
        child_labels = [c.label for c in subpart.children]
        self.assertEqual([['8675', '309'], ['8675', '310']], child_labels)

    def test_build_subjgrp(self):
        with XMLBuilder("SUBJGRP") as ctx:
            ctx.HD(u"Changes of Ownership")
            with ctx.SECTION():
                ctx.SECTNO(u"§ 479.42")
                ctx.SUBJECT("Changes through death of owner.")
                ctx.P(u"Whenever any person who has paid […] conditions.")
            with ctx.SECTION():
                ctx.SECTNO(u"§ 479.43")
                ctx.SUBJECT("Changes through bankruptcy of owner.")
                ctx.P(u"A receiver or referee in bankruptcy may […] paid.")
                ctx.P("(a) something something")
        subpart = reg_text.build_subjgrp('479', ctx.xml, [])
        self.assertEqual(subpart.node_type, 'subpart')
        self.assertEqual(len(subpart.children), 2)
        self.assertEqual(subpart.label, ['479', 'Subjgrp', 'CoO'])
        child_labels = [c.label for c in subpart.children]
        self.assertEqual([['479', '42'], ['479', '43']], child_labels)

    def test_get_markers(self):
        text = u'(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
        markers = reg_text.get_markers(text, mtypes.STARS_TAG)
        self.assertEqual(markers, [u'a', u'1'])

    def _split_by_markers_results(self, text):
        """DRY conversion between a paragraph text and corresponding
        (markers, text, tagged)"""
        xml = etree.fromstring(u'<ROOT><P>{}</P><STARS/></ROOT>'.format(text))
        results = reg_text.split_by_markers(xml[0])
        return list(zip(*results))    # unzips...

    def test_split_by_markers(self):
        text = u'(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
        markers, text, tagged = self._split_by_markers_results(text)
        self.assertEqual(markers, (u'a', u'1'))
        self.assertEqual(text, (u'(a) Transfer —', u'(1) Notice. follow'))
        self.assertEqual(tagged, (u'(a) <E T="03">Transfer </E>—',
                                  u'(1) <E T="03">Notice.</E> follow'))

    def test_split_by_markers_emph(self):
        text = '(A) aaaa. (<E T="03">1</E>) 1111'
        markers, text, tagged = self._split_by_markers_results(text)
        self.assertEqual(markers, ('A', '<E T="03">1</E>'))
        self.assertEqual(text, ('(A) aaaa. ', '(1) 1111'))
        self.assertEqual(tagged, ('(A) aaaa. ', '(<E T="03">1</E>) 1111'))

    def test_split_by_markers_deceptive_single(self):
        """Don't treat a single marker differently than multiple, there might
        be prefix text"""
        text = 'Words then. (a) a subparagraph'
        markers, text, tagged = self._split_by_markers_results(text)
        self.assertEqual(markers, (mtypes.MARKERLESS, 'a'))
        self.assertEqual(text, ('Words then. ', '(a) a subparagraph'))
        self.assertEqual(tagged, text)

    def test_get_markers_bad_citation(self):
        text = '(vi)<E T="03">Keyterm.</E>The information required by '
        text += 'paragraphs (a)(2), (a)(4)(iii), (a)(5), (b) through (d), '
        text += '(f), and (g) with respect to something, (i), (j), (l) '
        text += 'through (p), (q)(1), and (r) with respect to something.'
        self.assertEqual(['vi'], reg_text.get_markers(text))

    def test_get_markers_collapsed(self):
        """Only find collapsed markers if they are followed by a marker in
        sequence"""
        text = u'(a) <E T="03">aaa</E>—(1) 111. (i) iii'
        self.assertEqual(reg_text.get_markers(text), ['a'])
        self.assertEqual(reg_text.get_markers(text, 'b'), ['a'])
        self.assertEqual(reg_text.get_markers(text, 'A'), ['a', '1', 'i'])
        self.assertEqual(reg_text.get_markers(text, 'ii'), ['a', '1', 'i'])
        self.assertEqual(reg_text.get_markers(text, mtypes.STARS_TAG),
                         ['a', '1', 'i'])
        self.assertEqual(reg_text.get_markers(text, '2'), ['a', '1'])

    @patch('regparser.tree.xml_parser.reg_text.content')
    def test_preprocess_xml(self, content):
        with XMLBuilder("CFRGRANULE") as ctx:
            with ctx.PART():
                with ctx.APPENDIX():
                    ctx.TAG("Other Text")
                    with ctx.GPH(DEEP=453, SPAN=2):
                        ctx.GID("ABCD.0123")
        content.Macros.return_value = [
            ("//GID[./text()='ABCD.0123']/..",
             """<HD SOURCE="HD1">Some Title</HD><GPH DEEP="453" SPAN="2">"""
             """<GID>EFGH.0123</GID></GPH>""")]
        reg_text.preprocess_xml(ctx.xml)

        with XMLBuilder("CFRGRANULE") as ctx2:
            with ctx2.PART():
                with ctx2.APPENDIX():
                    ctx2.TAG("Other Text")
                    ctx2.HD("Some Title", SOURCE="HD1")
                    with ctx2.GPH(DEEP=453, SPAN=2):
                        ctx2.GID("EFGH.0123")
        self.assertEqual(ctx.xml_str, ctx2.xml_str)

    def test_build_from_section_double_alpha(self):
        # Ensure we match a hierarchy like (x), (y), (z), (aa), (bb)…
        with XMLBuilder("SECTION") as ctx:
            ctx.SECTNO(u"§ 8675.309")
            ctx.SUBJECT("Definitions.")
            ctx.P("(aa) This is what things mean:")
        node = reg_text.build_from_section('8675', ctx.xml)[0]
        child = node.children[0]
        self.assertEqual('(aa) This is what things mean:', child.text.strip())
        self.assertEqual(['8675', '309', 'aa'], child.label)

    def test_build_tree_with_subjgrp(self):
        """XML with SUBJGRPs where SUBPARTs are shouldn't cause a problem"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.PART():
                ctx.EAR("Pt. 123")
                ctx.HD(u"PART 123—SOME STUFF", SOURCE="HED")
                with ctx.SUBPART():
                    ctx.HD(u"Subpart A—First subpart")
                with ctx.SUBJGRP():
                    ctx.HD(u"Changes of Ownership")
                with ctx.SUBPART():
                    ctx.HD(u"Subpart B—First subpart")
                with ctx.SUBJGRP():
                    ctx.HD(u"Another Top Level")
        node = reg_text.build_tree(ctx.xml)
        self.assertEqual(node.label, ['123'])
        self.assertEqual(4, len(node.children))
        subpart_a, subjgrp_1, subpart_b, subjgrp_2 = node.children
        self.assertEqual(subpart_a.label, ['123', 'Subpart', 'A'])
        self.assertEqual(subpart_b.label, ['123', 'Subpart', 'B'])
        self.assertEqual(subjgrp_1.label, ['123', 'Subjgrp', 'CoO'])
        self.assertEqual(subjgrp_2.label, ['123', 'Subjgrp', 'ATL'])

    def test_initial_markers(self):
        """Should not find any collapsed markers and should find all of the
        markers at the beginning of the text"""
        text = '(k)(2)(iii) abc (j)'
        result = [m for m in reg_text.initial_markers(text)]
        self.assertEqual(['k', '2', 'iii'], result)

        text = '(i)(A) The minimum period payment'
        result = [m for m in reg_text.initial_markers(text)]
        self.assertEqual(['i', 'A'], result)

    def test_collapsed_markers(self):
        """We're expecting to find collapsed markers when they have certain
        prefixes, but not when they are part of a citation or do not have the
        appropriate prefix"""
        text = u'(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
        self.assertEqual([u'1'], reg_text.collapsed_markers(text))

        text = u'(a) <E T="03">Blah </E>means (1) <E T="03">Notice.</E> follow'
        self.assertEqual([u'1'], reg_text.collapsed_markers(text))

        text = '(1) See paragraph (a) for more'
        self.assertEqual([], reg_text.collapsed_markers(text))

        text = '(a) (1) More content'
        self.assertEqual([], reg_text.collapsed_markers(text))

        text = u'(a) <E T="03">Transfer—</E>(1) <E T="03">Notice.</E> follow'
        self.assertEqual([u'1'], reg_text.collapsed_markers(text))

        text = u'(a) <E T="03">Keyterm</E>—(1)(i) Content'
        self.assertEqual(['1', 'i'], reg_text.collapsed_markers(text))

        text = "(C) The information required by paragraphs (a)(2), "
        text += "(a)(4)(iii), (a)(5), (b) through (d), (i), (l) through (p)"
        self.assertEqual([], reg_text.collapsed_markers(text))

    def test_next_marker_found(self):
        """Find the first paragraph marker following a paragraph"""
        with XMLBuilder("ROOT") as ctx:
            ctx.P("(A) AAA")
            ctx.PRTPART()
            ctx.P("(d) ddd")
            ctx.P("(1) 111")
        self.assertEqual(reg_text.next_marker(ctx.xml[0]), 'd')

    def test_next_marker_stars(self):
        """STARS tag has special significance."""
        with XMLBuilder("ROOT") as ctx:
            ctx.P("(A) AAA")
            ctx.PRTPART()
            ctx.STARS()
            ctx.P("(d) ddd")
            ctx.P("(1) 111")
        self.assertEqual(reg_text.next_marker(ctx.xml[0]), mtypes.STARS_TAG)

    def test_next_marker_none(self):
        """If no marker is present, return None"""
        with XMLBuilder("ROOT") as ctx:
            ctx.P("(1) 111")
            ctx.P("Content")
            ctx.P("(i) iii")
        self.assertIsNone(reg_text.next_marker(ctx.xml[0]))


class RegtextParagraphProcessorTests(TestCase):
    def test_process_markerless_collapsed(self):
        """Should be able to find collapsed markers in a markerless
        paragraph"""
        with XMLBuilder("ROOT") as ctx:
            ctx.P("Intro text")
            ctx.child_from_string(
                '<P><E T="03">Some term.</E> (a) First definition</P>')
            ctx.P("(b) Second definition")
        root = Node(label=['111', '22'])
        root = reg_text.RegtextParagraphProcessor().process(ctx.xml, root)
        root = NodeAccessor(root)

        self.assertEqual(['111', '22'], root.label)
        self.assertEqual(2, len(root.child_labels))
        self.assertTrue(all(c.is_markerless for c in root.children))
        keyterm_label = root.child_labels[1]
        self.assertTrue(len(keyterm_label) > 5)
        self.assertEqual(['a', 'b'], root[keyterm_label].child_labels)

    def test_process_nested_uscode(self):
        with XMLBuilder("ROOT") as ctx:
            ctx.P("Some intro")
            with ctx.EXTRACT():
                ctx.HD("The U.S. Code!")
                with ctx.USCODE():
                    ctx.P("(x)(1) Some content")
                    ctx.P("(A) Sub-sub-paragraph")
                    ctx.P("(i)(I) Even more nested")
        root = reg_text.RegtextParagraphProcessor().process(ctx.xml, Node())
        root = NodeAccessor(root)

        self.assertEqual(root['p1'].text, "Some intro")
        self.assertEqual(root['p2']['p1'].title, 'The U.S. Code!')
        code = root['p2']['p2']
        self.assertEqual(code.source_xml.tag, 'USCODE')
        self.assertEqual(code['x'].text, '(x)')
        self.assertEqual(code['x']['1'].text, '(1) Some content')
        self.assertEqual(code['x']['1']['A'].text, '(A) Sub-sub-paragraph')
        self.assertEqual(code['x']['1']['A']['i'].text, '(i)')
        self.assertEqual(code['x']['1']['A']['i']['I'].text,
                         '(I) Even more nested')


def test_get_subpart_group_title():
    with XMLBuilder("SUBPART") as ctx:
        ctx.HD(u"Subpart A—First subpart")
    subpart_title = reg_text.get_subpart_group_title(ctx.xml)
    assert subpart_title == u'Subpart A—First subpart'


def test_get_subpart_group_title_reserved():
    with XMLBuilder("SUBPART") as ctx:
        ctx.RESERVED("Subpart J [Reserved]")
    subpart_title = reg_text.get_subpart_group_title(ctx.xml)
    assert subpart_title == u'Subpart J [Reserved]'


def test_get_subpart_group_title_em():
    with XMLBuilder("SUBPART") as ctx:
        ctx.child_from_string(
            u'<HD SOURCE="HED">Subpart B—<E T="0714">Partes</E> Review</HD>')
    subpart_title = reg_text.get_subpart_group_title(ctx.xml)
    assert subpart_title == u'Subpart B—Partes Review'
