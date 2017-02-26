# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from mock import Mock

from regparser.notice.amendments import fetch, section
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser.preprocessors import preprocess_amdpars


def test_find_section():
    with XMLBuilder('REGTEXT') as ctx:
        ctx.AMDPAR("In 200.1 revise paragraph (b) as follows:")
        with ctx.SECTION():
            ctx.SECTNO("200.1")
            ctx.SUBJECT("Authority and Purpose.")
            ctx.P(" (b) This part is very important. ")
        ctx.AMDPAR("In 200.3 revise paragraph (b)(1) as follows:")
        with ctx.SECTION():
            ctx.SECTNO("200.3")
            ctx.SUBJECT("Definitions")
            ctx.P(" (b)(1) Define a term here. ")

    amdpar_xml = ctx.xml.xpath('//AMDPAR')[0]
    sect = section.find_section(amdpar_xml)
    assert sect.tag == 'SECTION'

    sectno_xml = sect.xpath('./SECTNO')[0]
    assert sectno_xml.text == '200.1'


def test_find_section_paragraphs():
    with XMLBuilder("REGTEXT") as ctx:
        with ctx.SECTION():
            ctx.SECTNO(" 205.4 ")
            ctx.SUBJECT("[Corrected]")
        ctx.AMDPAR("3. In § 105.1, revise paragraph (b) to read as follows:")
        ctx.P("(b) paragraph 1")

    amdpar = ctx.xml.xpath('//AMDPAR')[0]
    sect = section.find_section(amdpar)
    assert sect is not None
    paragraphs = [p for p in sect if p.tag == 'P']
    assert paragraphs[0].text == '(b) paragraph 1'


def test_find_lost_section():
    with XMLBuilder("PART") as ctx:
        with ctx.REGTEXT():
            ctx.AMDPAR("3. In § 105.1, revise paragraph (b) to read as "
                       "follows:")
        with ctx.REGTEXT():
            with ctx.SECTION():
                ctx.SECTNO(" 205.4 ")
                ctx.SUBJECT("[Corrected]")
    amdpar = ctx.xml.xpath('//AMDPAR')[0]
    sect = section.find_lost_section(amdpar)
    assert sect is not None


def test_find_section_lost():
    with XMLBuilder("PART") as ctx:
        with ctx.REGTEXT():
            ctx.AMDPAR("3. In § 105.1, revise paragraph (b) to read as "
                       "follows:")
        with ctx.REGTEXT():
            with ctx.SECTION():
                ctx.SECTNO(" 205.4 ")
                ctx.SUBJECT("[Corrected]")
    amdpar = ctx.xml.xpath('//AMDPAR')[0]
    sect = section.find_section(amdpar)
    assert sect is not None


@pytest.fixture
def content_plugin_installed(monkeypatch):
    # turn on the section plugin
    monkeypatch.setattr(fetch, 'instantiate_if_possible', Mock(return_value=[
        section.content_for_regtext
    ]))


@pytest.mark.usefixtures('content_plugin_installed')
def test_introductory_text():
    """ Sometimes notices change just the introductory text of a paragraph
    (instead of changing the entire paragraph tree).  """
    with XMLBuilder("REGTEXT", PART="106", TITLE="12") as ctx:
        ctx.AMDPAR("3. In § 106.2, revise the introductory text to read:")
        with ctx.SECTION():
            ctx.SECTNO("§ 106.2")
            ctx.SUBJECT(" Definitions ")
            ctx.P(" Except as otherwise provided, the following apply. ")
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    change = dict(amendment['changes'])['106-2'][0]
    assert change.get('field') == '[text]'


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_insert_in_order():
    amdpar = '[insert-in-order] [label:123-45-p6]'
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(TITLE="10"):
            ctx.AMDPAR(amdpar)
            with ctx.SECTION():
                ctx.SECTNO("§ 123.45")
                ctx.SUBJECT("Some Subject.")
                ctx.STARS()
                ctx.P("This is the sixth paragraph")
                ctx.STARS()
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    changes = dict(amendment['changes'])

    assert amendment['instruction'] == amdpar
    assert amendment['cfr_part'] == '123'
    assert ['123-45-p6'] == list(changes.keys())
    assert changes['123-45-p6'][0]['action'] == 'INSERT'


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_mix_regs():
    """Some notices apply to multiple regs. For now, just ignore the
    sections not associated with the reg we're focused on"""
    amdpar1 = "3. In § 105.1, revise paragraph (a) to read as follows:"
    amdpar2 = "3. In § 106.3, revise paragraph (b) to read as follows:"
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(PART="105", TITLE="12"):
            ctx.AMDPAR(amdpar1)
            with ctx.SECTION():
                ctx.SECTNO("§ 105.1")
                ctx.SUBJECT("105Purpose.")
                ctx.P("(a) 105Content")
        with ctx.REGTEXT(PART="106", TITLE="12"):
            ctx.AMDPAR(amdpar2)
            with ctx.SECTION():
                ctx.SECTNO("§ 106.3")
                ctx.SUBJECT("106Purpose.")
                ctx.P("(b) Content")
    preprocess_amdpars(ctx.xml)

    amd1, amd2 = fetch.fetch_amendments(ctx.xml)
    assert amd1['instruction'] == amdpar1
    assert amd1['cfr_part'] == '105'
    assert amd2['instruction'] == amdpar2
    assert amd2['cfr_part'] == '106'
    assert ['105-1-a'] == [c[0] for c in amd1['changes']]
    assert ['106-3-b'] == [c[0] for c in amd2['changes']]


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_multiple_sections():
    """Regression test verifying multiple SECTIONs in the same REGTEXT"""
    amdpar1 = "1. Modify § 111.22 by revising paragraph (b)"
    amdpar2 = "2. Modify § 111.33 by revising paragraph (c)"
    with XMLBuilder("REGTEXT", PART="111") as ctx:
        ctx.AMDPAR(amdpar1)
        with ctx.SECTION():
            ctx.SECTNO("§ 111.22")
            ctx.SUBJECT("Subject Here.")
            ctx.STARS()
            ctx.P("(b) Revised second paragraph")
        ctx.AMDPAR(amdpar2)
        with ctx.SECTION():
            ctx.SECTNO("§ 111.33")
            ctx.SUBJECT("Another Subject")
            ctx.STARS()
            ctx.P("(c) Revised third paragraph")
    preprocess_amdpars(ctx.xml)

    amd1, amd2 = fetch.fetch_amendments(ctx.xml)
    assert amd1['instruction'] == amdpar1
    assert amd1['cfr_part'] == '111'
    assert ['111-22-b'] == [c[0] for c in amd1['changes']]
    assert amd2['instruction'] == amdpar2
    assert amd2['cfr_part'] == '111'
    assert ['111-33-c'] == [c[0] for c in amd2['changes']]


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_markerless():
    amdpar = "1. Revise [label:105-11-p5] as blah"
    with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
        ctx.AMDPAR(amdpar)
        with ctx.SECTION():
            ctx.SECTNO("§ 105.11")
            ctx.SUBJECT("Purpose.")
            ctx.STARS()
            ctx.P("Some text here")
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    changes = dict(amendment['changes'])

    assert amendment['instruction'] == amdpar
    assert amendment['cfr_part'] == '105'
    assert ['105-11-p5'] == list(changes.keys())
    changes = changes['105-11-p5'][0]
    assert changes['action'] == 'PUT'


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_no_nodes():
    amdpar = "1. In § 104.13, paragraph (b) is removed"
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(PART="104", TITLE="12"):
            ctx.AMDPAR(amdpar)
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    changes = dict(amendment['changes'])

    assert amendment['instruction'] == amdpar
    assert amendment['cfr_part'] == '104'
    assert '104-13-b' in changes
    assert changes['104-13-b'][0]['action'] == 'DELETE'


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_multiple_in_same_parent():
    amdpar1 = "1. In § 105.1, revise paragraph (b) to read as follows:"
    amdpar2 = "2. Also, revise paragraph (c):"
    with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
        ctx.AMDPAR(amdpar1)
        ctx.AMDPAR(amdpar2)
        with ctx.SECTION():
            ctx.SECTNO("§ 105.1")
            ctx.SUBJECT("Purpose.")
            ctx.STARS()
            ctx.P("(b) This part carries out.")
            ctx.P("(c) More stuff")
    preprocess_amdpars(ctx.xml)

    amd1, amd2 = fetch.fetch_amendments(ctx.xml)
    changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
    assert amd1['instruction'] == amdpar1
    assert amd1['cfr_part'] == '105'
    assert amd2['instruction'] == amdpar2
    assert amd2['cfr_part'] == '105'
    assert ['105-1-b'] == list(changes1.keys())
    assert ['105-1-c'] == list(changes2.keys())

    changes = changes1['105-1-b'][0]
    assert changes['action'] == 'PUT'
    assert changes['node']['text'] == '(b) This part carries out.'
    changes = changes2['105-1-c'][0]
    assert changes['action'] == 'PUT'
    assert changes['node']['text'] == '(c) More stuff'


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_section():
    amdpar = "3. In § 105.1, revise paragraph (b) to read as follows:"
    with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
        ctx.AMDPAR(amdpar)
        with ctx.SECTION():
            ctx.SECTNO("§ 105.1")
            ctx.SUBJECT("Purpose.")
            ctx.STARS()
            ctx.P("(b) This part carries out.")
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    changes = dict(amendment['changes'])

    assert amendment['instruction'] == amdpar
    assert amendment['cfr_part'] == '105'
    assert ['105-1-b'] == list(changes.keys())

    changes = changes['105-1-b'][0]
    assert changes['action'] == 'PUT'
    assert changes['node']['text'] == '(b) This part carries out.'
