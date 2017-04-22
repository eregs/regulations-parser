# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mock import Mock

from regparser.notice.amendments import appendix, fetch, section
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser.preprocessors import preprocess_amdpars


def test_parse_appendix(monkeypatch):
    process = Mock()
    monkeypatch.setattr(appendix, 'process_appendix', process)

    with XMLBuilder("ROOT") as ctx:
        ctx.AMDPAR("1. Adding Appendix R and S")
        ctx.HD("Appendix R to Part 1234", SOURCE="HD1")
        with ctx.EXTRACT():
            ctx.P("R1")
            ctx.P("R2")
        ctx.HD("Appendix S to Part 1234", SOURCE="HD1")
        with ctx.EXTRACT():
            ctx.P("S1")
            ctx.P("S2")

    appendix.parse_appendix(ctx.xml, '1234', 'S')
    assert process.call_count == 1
    extract = process.call_args[0][0]
    assert ['Appendix S to Part 1234', 'S1', 'S2'] == [n.text for n in extract]

    appendix.parse_appendix(ctx.xml, '1234', 'R')
    assert process.call_count == 2
    extract = process.call_args[0][0]
    assert ['Appendix R to Part 1234', 'R1', 'R2'] == [n.text for n in extract]


def test_process_amendments_context(monkeypatch):
    """Context should carry over between REGTEXTs"""
    # turn on the interpretations plugin
    monkeypatch.setattr(fetch, 'instantiate_if_possible', Mock(return_value=[
        appendix.content_for_appendix, section.content_for_regtext
    ]))
    amdpar1 = "3. In § 106.1, revise paragraph (a) to read as follows:"
    amdpar2 = "3. Add appendix C"
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(TITLE="12"):
            ctx.AMDPAR(amdpar1)
            with ctx.SECTION():
                ctx.SECTNO("§ 106.1")
                ctx.SUBJECT("Some Subject.")
                ctx.P("(a) Something new")
        with ctx.REGTEXT(TITLE="12"):
            ctx.AMDPAR(amdpar2)
            ctx.HD("Appendix C to Part 106", SOURCE="HD1")
            with ctx.EXTRACT():
                ctx.P("Text")
    preprocess_amdpars(ctx.xml)

    amd1, amd2 = fetch.fetch_amendments(ctx.xml)
    assert amd1['instruction'] == amdpar1
    assert amd1['cfr_part'] == '106'
    assert amd2['instruction'] == amdpar2
    assert amd2['cfr_part'] == '106'
    assert ['106-1-a'] == [c[0] for c in amd1['changes']]
    assert ['106-C', '106-C-p1'] == list(sorted(c[0] for c in amd2['changes']))


def test_content_for_appendix_regression_369():
    """Regression test for modifications to a top-level element"""
    with XMLBuilder('EREGS_INSTRUCTIONS', final_context='2-?-201') as ctx:
        ctx.POST(label='2[title]')
        ctx.POST(label='2-?-200')
        ctx.POST(label='2-?-201')
    assert appendix.content_for_appendix(ctx.xml) is None
