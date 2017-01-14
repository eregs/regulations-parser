# -*- coding: utf-8 -*-
import pytest
from lxml import etree
from mock import Mock

from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.gpo_cfr import builder


def test_get_title():
    with XMLBuilder() as ctx:
        with ctx.PART():
            ctx.HD("regulation title")
    assert builder.get_title(ctx.xml) == 'regulation title'
    assert builder.get_title(ctx.xml[0]) == 'regulation title'


@pytest.mark.parametrize('xml_str', [
    "<PART><EAR>Pt. 204</EAR></PART>",
    "<FDSYS><HEADING>PART 204</HEADING></FDSYS>",
    "<FDSYS><GRANULENUM>204</GRANULENUM></FDSYS>",
])
def test_get_reg_part(xml_str):
    """Test various formats for the Regulation part to be present in a
    CFR-XML document"""
    assert builder.get_reg_part(etree.fromstring(xml_str)) == '204'
    xml_str = '<SOME><NESTING>{0}</NESTING></SOME>'.format(xml_str)
    assert builder.get_reg_part(etree.fromstring(xml_str)) == '204'


def test_get_reg_part_fr_notice_style():
    with XMLBuilder("REGTEXT", PART=204) as ctx:
        ctx.SECTION("\n")
    assert builder.get_reg_part(ctx.xml) == '204'


def test_preprocess_xml(monkeypatch):
    with XMLBuilder("CFRGRANULE") as ctx:
        with ctx.PART():
            with ctx.APPENDIX():
                ctx.TAG("Other Text")
                with ctx.GPH(DEEP=453, SPAN=2):
                    ctx.GID("ABCD.0123")
    content = Mock()
    content.Macros.return_value = [
        ("//GID[./text()='ABCD.0123']/..",
         """<HD SOURCE="HD1">Some Title</HD><GPH DEEP="453" SPAN="2">"""
         """<GID>EFGH.0123</GID></GPH>""")]
    monkeypatch.setattr(builder, 'content', content)
    builder.preprocess_xml(ctx.xml)

    with XMLBuilder("CFRGRANULE") as ctx2:
        with ctx2.PART():
            with ctx2.APPENDIX():
                ctx2.TAG("Other Text")
                ctx2.HD("Some Title", SOURCE="HD1")
                with ctx2.GPH(DEEP=453, SPAN=2):
                    ctx2.GID("EFGH.0123")
    assert ctx.xml_str == ctx2.xml_str


def test_build_tree_with_subjgrp():
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
    assert node.label == ['123']
    assert len(node.children) == 4
    subpart_a, subjgrp_1, subpart_b, subjgrp_2 = node.children
    assert subpart_a.label == ['123', 'Subpart', 'A']
    assert subpart_b.label == ['123', 'Subpart', 'B']
    assert subjgrp_1.label == ['123', 'Subjgrp', 'CoO']
    assert subjgrp_2.label == ['123', 'Subjgrp', 'ATL']
