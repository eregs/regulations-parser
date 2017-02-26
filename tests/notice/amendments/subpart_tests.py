# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from mock import Mock

from regparser.notice.amdparser import Amendment
from regparser.notice.amendments import fetch, section, subpart
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser.preprocessors import preprocess_amdpars


@pytest.fixture
def content_plugin_installed(monkeypatch):
    # turn on the subpart plugin
    monkeypatch.setattr(fetch, 'instantiate_if_possible', Mock(return_value=[
        subpart.content_for_new_subpart, section.content_for_regtext
    ]))


def test_process_designate_subpart():
    amended_label = Amendment('MOVE_INTO_SUBPART', '200-?-1-a',
                              '205-Subpart:A')

    subpart_changes = subpart.process_designate_subpart(amended_label)

    assert '200-1-a' == subpart_changes.label_id
    change = subpart_changes.content
    assert change['destination'] == ['205', 'Subpart', 'A']
    assert change['action'] == 'DESIGNATE'


@pytest.mark.usefixtures('content_plugin_installed')
def test_multiple_changes(monkeypatch):
    """ A notice can have two modifications to a paragraph. """
    amdpar1 = ("2. Designate §§ 106.1 through 106.3 as subpart A under "
               "the heading.")
    amdpar2 = "3. In § 106.2, revise the introductory text to read:"
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(PART="106", TITLE="12"):
            ctx.AMDPAR(amdpar1)
        with ctx.REGTEXT(PART="106", TITLE="12"):
            ctx.AMDPAR(amdpar2)
            with ctx.SECTION():
                ctx.SECTNO("§ 106.2")
                ctx.SUBJECT(" Definitions ")
                ctx.P(" Except as otherwise provided, the following "
                      "apply. ")
    preprocess_amdpars(ctx.xml)

    amd1, amd2 = fetch.fetch_amendments(ctx.xml)
    changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
    assert amd1['instruction'] == amdpar1
    assert amd1['cfr_part'] == '106'
    assert amd2['instruction'] == amdpar2
    assert amd2['cfr_part'] == '106'
    assert len(changes1['106-2']) == 1
    assert len(changes2['106-2']) == 1


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments_subpart(monkeypatch):
    with XMLBuilder("RULE") as ctx:
        with ctx.REGTEXT(PART="105", TITLE="12"):
            ctx.AMDPAR("3. In § 105.1, revise paragraph (b) to read as"
                       "follows:")
            with ctx.SECTION():
                ctx.SECTNO("§ 105.1")
                ctx.SUBJECT("Purpose.")
                ctx.STARS()
                ctx.P("(b) This part carries out.")
        with ctx.REGTEXT(PART="105", TITLE="12"):
            ctx.AMDPAR("6. Add subpart B to read as follows:")
            with ctx.CONTENTS():
                with ctx.SUBPART():
                    ctx.SECHD("Sec.")
                    ctx.SECTNO("105.30")
                    ctx.SUBJECT("First In New Subpart.")
            with ctx.SUBPART():
                ctx.HD("Subpart B—Requirements", SOURCE="HED")
                with ctx.SECTION():
                    ctx.SECTNO("105.30")
                    ctx.SUBJECT("First In New Subpart")
                    ctx.P("For purposes of this subpart, the follow "
                          "apply:")
                    ctx.P('(a) "Agent" means agent.')

    preprocess_amdpars(ctx.xml)

    subpart_amendment = fetch.fetch_amendments(ctx.xml)[1]
    changes = dict(subpart_amendment['changes'])

    assert '105-Subpart-B' in changes
    assert '105-30-a' in changes
    assert '105-30' in changes


@pytest.mark.usefixtures('content_plugin_installed')
def test_process_amendments():
    amdpar = ("2. Designate §§ 105.1 through 105.3 as subpart A under the "
              "heading.")
    with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
        with ctx.SUBPART():
            ctx.HD("Subpart A—General", SOURCE="HED")
        ctx.AMDPAR(amdpar)
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    changes = dict(amendment['changes'])

    assert amendment['instruction'] == amdpar
    assert amendment['cfr_part'] == '105'
    assert ['105-1', '105-2', '105-3'] == list(sorted(changes.keys()))
    for change_list in changes.values():
        assert len(change_list) == 1
        change = change_list[0]
        assert change['destination'] == ['105', 'Subpart', 'A']
        assert change['action'] == 'DESIGNATE'
