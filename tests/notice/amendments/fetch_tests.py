# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from regparser.notice import changes
from regparser.notice.amdparser import Amendment
from regparser.notice.amendments import fetch
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.struct import Node
from regparser.tree.xml_parser.preprocessors import preprocess_amdpars


def test_process_amendments_authority():
    amdpar = ('1. The authority citation for 27 CFR Part 555 continues to '
              'read as follows:')
    auth = '18 U.S.C. 847.'
    with XMLBuilder("ROOT") as ctx:
        with ctx.REGTEXT(TITLE="27", PART="555"):
            ctx.AMDPAR(amdpar)
            with ctx.AUTH():
                ctx.HD("Authority:", SOURCE="HED")
                ctx.P(auth)
    preprocess_amdpars(ctx.xml)

    amendment = fetch.fetch_amendments(ctx.xml)[0]
    assert amendment['instruction'] == amdpar
    assert amendment['cfr_part'] == '555'
    assert amendment['authority'] == auth
    assert 'changes' not in amendment


def test_create_xmlless_changes():
    labels_amended = [Amendment('DELETE', '200-?-2-a'),
                      Amendment('MOVE', '200-?-2-b', '200-?-2-c')]
    notice_changes = changes.NoticeChanges()
    for amendment in labels_amended:
        fetch.create_xmlless_change(amendment, notice_changes)

    delete = notice_changes[None]['200-2-a'][0]
    move = notice_changes[None]['200-2-b'][0]
    assert delete == {'action': 'DELETE'}
    assert move == {'action': 'MOVE', 'destination': ['200', '2', 'c']}


def test_create_xml_changes_reserve():
    labels_amended = [Amendment('RESERVE', '200-?-2-a')]

    n2a = Node('[Reserved]', label=['200', '2', 'a'])
    n2 = Node('n2', label=['200', '2'], children=[n2a])
    root = Node('root', label=['200'], children=[n2])

    notice_changes = changes.NoticeChanges()
    fetch.create_xml_changes(labels_amended, root, notice_changes)

    reserve = notice_changes[None]['200-2-a'][0]
    assert reserve['action'] == 'RESERVE'
    assert reserve['node']['text'] == '[Reserved]'


def test_create_xml_changes_stars():
    labels_amended = [Amendment('PUT', '200-?-2-a')]
    n2a1 = Node('(1) Content', label=['200', '2', 'a', '1'])
    n2a2 = Node('(2) Content', label=['200', '2', 'a', '2'])
    n2a = Node('(a) * * *', label=['200', '2', 'a'], children=[n2a1, n2a2])
    n2 = Node('n2', label=['200', '2'], children=[n2a])
    root = Node('root', label=['200'], children=[n2])

    notice_changes = changes.NoticeChanges()
    fetch.create_xml_changes(labels_amended, root, notice_changes)
    data = notice_changes[None]

    for label in ('200-2-a-1', '200-2-a-2'):
        assert label in data
        assert len(data[label]) == 1
        change = data[label][0]
        assert change['action'] == 'PUT'
        assert 'field' not in change

    assert '200-2-a' in data
    assert len(data['200-2-a']) == 1
    change = data['200-2-a'][0]
    assert change['action'] == 'KEEP'
    assert 'field' not in change


def test_create_xml_changes_stars_hole():
    labels_amended = [Amendment('PUT', '200-?-2-a')]
    n2a1 = Node('(1) * * *', label=['200', '2', 'a', '1'])
    n2a2 = Node('(2) a2a2a2', label=['200', '2', 'a', '2'])
    n2a = Node('(a) aaa', label=['200', '2', 'a'], children=[n2a1, n2a2])
    n2 = Node('n2', label=['200', '2'], children=[n2a])
    root = Node('root', label=['200'], children=[n2])

    notice_changes = changes.NoticeChanges()
    fetch.create_xml_changes(labels_amended, root, notice_changes)

    data = notice_changes[None]
    for label in ('200-2-a', '200-2-a-2'):
        assert label in data
        assert len(data[label]) == 1
        change = data[label][0]
        assert change['action'] == 'PUT'
        assert 'field' not in change

    assert '200-2-a-1' in data
    assert len(data['200-2-a-1']) == 1
    change = data['200-2-a-1'][0]
    assert change['action'] == 'KEEP'
    assert 'field' not in change


def test_create_xml_changes_child_stars():
    labels_amended = [Amendment('PUT', '200-?-2-a')]
    with XMLBuilder("ROOT") as ctx:
        ctx.P("(a) Content")
        ctx.STARS()
    n2a = Node('(a) Content', label=['200', '2', 'a'],
               source_xml=ctx.xml.xpath('//P')[0])
    n2b = Node('(b) Content', label=['200', '2', 'b'])
    n2 = Node('n2', label=['200', '2'], children=[n2a, n2b])
    root = Node('root', label=['200'], children=[n2])

    notice_changes = changes.NoticeChanges()
    fetch.create_xml_changes(labels_amended, root, notice_changes)
    data = notice_changes[None]

    assert '200-2-a' in data
    assert len(data['200-2-a']) == 1
    change = data['200-2-a'][0]
    assert change['action'] == 'PUT'
    assert 'field' not in change

    n2a.text = n2a.text + ":"
    n2a.source_xml.text = n2a.source_xml.text + ":"

    notice_changes = changes.NoticeChanges()
    fetch.create_xml_changes(labels_amended, root, notice_changes)
    data = notice_changes[None]

    assert '200-2-a' in data
    assert len(data['200-2-a']) == 1
    change = data['200-2-a'][0]
    assert change['action'] == 'PUT'
    assert change.get('field') == '[text]'
