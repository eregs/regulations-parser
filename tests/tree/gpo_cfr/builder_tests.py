# -*- coding: utf-8 -*-
from unittest import TestCase

from lxml import etree
from mock import patch

from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.gpo_cfr import builder


class RegTextTest(TestCase):
    def test_get_title(self):
        with XMLBuilder("PART") as ctx:
            ctx.HD("regulation title")
        title = builder.get_title(ctx.xml)
        self.assertEqual(u'regulation title', title)

    def test_get_reg_part(self):
        """Test various formats for the Regulation part to be present in a
        CFR-XML document"""
        xmls = []
        xmls.append(u"<PART><EAR>Pt. 204</EAR></PART>")
        xmls.append(u"<FDSYS><HEADING>PART 204</HEADING></FDSYS>")
        xmls.append(u"<FDSYS><GRANULENUM>204</GRANULENUM></FDSYS>")
        for xml_str in xmls:
            part = builder.get_reg_part(etree.fromstring(xml_str))
            self.assertEqual(part, '204')

    def test_get_reg_part_fr_notice_style(self):
        with XMLBuilder("REGTEXT", PART=204) as ctx:
            ctx.SECTION("\n")
        part = builder.get_reg_part(ctx.xml)
        self.assertEqual(part, '204')

    @patch('regparser.tree.gpo_cfr.builder.content')
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
        builder.preprocess_xml(ctx.xml)

        with XMLBuilder("CFRGRANULE") as ctx2:
            with ctx2.PART():
                with ctx2.APPENDIX():
                    ctx2.TAG("Other Text")
                    ctx2.HD("Some Title", SOURCE="HD1")
                    with ctx2.GPH(DEEP=453, SPAN=2):
                        ctx2.GID("EFGH.0123")
        self.assertEqual(ctx.xml_str, ctx2.xml_str)

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
        node = builder.build_tree(ctx.xml)
        self.assertEqual(node.label, ['123'])
        self.assertEqual(4, len(node.children))
        subpart_a, subjgrp_1, subpart_b, subjgrp_2 = node.children
        self.assertEqual(subpart_a.label, ['123', 'Subpart', 'A'])
        self.assertEqual(subpart_b.label, ['123', 'Subpart', 'B'])
        self.assertEqual(subjgrp_1.label, ['123', 'Subjgrp', 'CoO'])
        self.assertEqual(subjgrp_2.label, ['123', 'Subjgrp', 'ATL'])
