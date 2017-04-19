# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mock import Mock

from interpparser import amendments
from regparser.notice.amendments import fetch, section
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser.preprocessors import preprocess_amdpars


def test_parse_interp(monkeypatch):
    interp_lib = Mock()
    monkeypatch.setattr(amendments, 'gpo_cfr', interp_lib)
    xmls = []
    with XMLBuilder("REGTEXT") as ctx:
        with ctx.EXTRACT():
            ctx.P("Something")
            ctx.STARS()
            ctx.HD("Supplement I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
    xmls.append(ctx.xml)

    with XMLBuilder("REGTEXT") as ctx:
        ctx.P("Something")
        ctx.STARS()
        with ctx.SUBSECT():
            ctx.HD("Supplement I")
        ctx.HD("A")
        ctx.T1("a")
        ctx.P("b")
    xmls.append(ctx.xml)

    with XMLBuilder("REGTEXT") as ctx:
        ctx.AMDPAR("1. In Supplement I to part 111, under...")
        ctx.P("Something")
        ctx.STARS()
        ctx.HD("SUPPLEMENT I")
        ctx.HD("A")
        ctx.T1("a")
        ctx.P("b")
    xmls.append(ctx.xml)

    with XMLBuilder("REGTEXT") as ctx:
        ctx.AMDPAR("1. In Supplement I to part 111, under...")
        ctx.P("Something")
        ctx.STARS()
        with ctx.APPENDIX():
            ctx.HD("SUPPLEMENT I")
        ctx.HD("A")
        ctx.T1("a")
        ctx.P("b")
        ctx.PRTPAGE()
    xmls.append(ctx.xml)

    for xml in xmls:
        amendments.parse_interp('111', xml)
        root, nodes = interp_lib.parse_from_xml.call_args[0]
        assert root.label == ['111', 'Interp']
        assert [n.tag for n in nodes] == ['HD', 'T1', 'P']


def test_parse_interp_subpart_confusion():
    with XMLBuilder("REGTEXT") as ctx:
        ctx.AMDPAR("1. In Supplement I to part 111, under Section 33, "
                   "paragraph 5 is added.")
        ctx.HD("Supplement I")
        with ctx.SUBPART():
            with ctx.SECTION():
                ctx.SECTNO("§ 111.33")
                ctx.SUBJECT("Stubby Subby")
                ctx.STARS()
                ctx.P("5. Some Content")
    interp = amendments.parse_interp('111', ctx.xml)
    assert len(interp.children) == 1
    c33 = interp.children[0]
    assert c33.label == ['111', '33', 'Interp']
    assert len(c33.children) == 1
    c335 = c33.children[0]
    assert c335.label == ['111', '33', 'Interp', '5']


def test_process_amendments_restart_new_section(monkeypatch):
    # turn on the interpretations plugin
    monkeypatch.setattr(fetch, 'instantiate_if_possible', Mock(return_value=[
        amendments.content_for_interpretations, section.content_for_regtext
    ]))

    amdpar1 = "1. In Supplement I to Part 104, comment 22(a) is added"
    amdpar2 = "3. In § 105.1, revise paragraph (b) to read as follows:"
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(PART="104", TITLE="12"):
            ctx.AMDPAR(amdpar1)
            ctx.HD("SUPPLEMENT I", SOURCE='HED')
            ctx.HD("22(a)", SOURCE='HD1')
            ctx.P("1. Content")
        with ctx.REGTEXT(PART="105", TITLE="12"):
            ctx.AMDPAR(amdpar2)
            with ctx.SECTION():
                ctx.SECTNO("§ 105.1")
                ctx.SUBJECT("Purpose.")
                ctx.STARS()
                ctx.P("(b) This part carries out.")
    preprocess_amdpars(ctx.xml)

    amd1, amd2 = fetch.fetch_amendments(ctx.xml)
    changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
    assert amd1['instruction'] == amdpar1
    assert amd1['cfr_part'] == '104'
    assert amd2['instruction'] == amdpar2
    assert amd2['cfr_part'] == '105'
    assert '104-22-a-Interp' in changes1
    assert '105-1-b' in changes2

    assert changes1['104-22-a-Interp'][0]['action'] == 'POST'
    assert changes2['105-1-b'][0]['action'] == 'PUT'


def test_content_for_interpretations_regression_369():
    """Regression test for modifications to a top-level element"""
    with XMLBuilder('EREGS_INSTRUCTIONS', final_context='2-?-201') as ctx:
        ctx.POST(label='2[title]')
        ctx.POST(label='2-?-200')
        ctx.POST(label='2-?-201')
    assert amendments.content_for_interpretations(ctx.xml) is None
