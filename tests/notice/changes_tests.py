# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from regparser.notice import changes
from regparser.notice.amdparser import Amendment
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.struct import Node, find


def _build_tree():
    n1 = Node('n1', label=['200', '1'])
    n2 = Node('n1i', label=['200', 1, 'i'])
    n3 = Node('n2', label=['200', '2'])
    n4 = Node('n3', label=['200', '3'])
    n5 = Node('n3a', label=['200', '3', 'a'])

    n1.children = [n2]
    n4.children = [n5]
    root = Node('root', label=['200'], children=[n1, n3, n4])
    return root


def test_find_candidate():
    root = _build_tree()
    result = changes.find_candidate(root, 'i', [])[0]
    assert 'n1i' == result.text

    n2c = Node('n3c', label=['200', '2', 'i', 'i'])
    n2 = find(root, '200-2')
    n2.children = [n2c]

    result = changes.find_candidate(root, 'i', [])[0]
    assert result.label == ['200', '2', 'i', 'i']


def test_not_find_candidate():
    root = _build_tree()
    result = changes.find_candidate(root, 'j', [])
    assert result == []


def test_find_candidate_impossible_label():
    n1 = Node('', label=['200', '1'])
    n1a = Node('', label=['200', '1', 'a'])

    n1a1i = Node('', label=['200', '1', 'a', '1', 'i'])
    n1a.children = [n1a1i]

    n1b = Node('', label=['200', '1', 'b'])
    n1i = Node('', label=['200', '1', 'i'])
    n1.children = [n1a, n1b, n1i]

    root = Node('root', label=['200'], children=[n1])
    candidate = changes.find_candidate(
        root, 'i', ['200-1-a', '200-1-b'])[0]

    assert candidate.label == ['200', '1', 'i']


def test_find_misparsed_node():
    n2 = Node('n1i', label=['200', 1, 'i'])
    root = _build_tree()

    result = {'action': 'PUT'}

    result = changes.find_misparsed_node(root, 'i', result, [])
    assert result['action'] == 'PUT'
    assert result['candidate']
    assert result['node'] == n2


def test_create_add_amendment():
    root = _build_tree()

    amendment = {'node': root, 'action': 'POST'}
    amendments = changes.create_add_amendment(amendment)
    assert len(amendments) == 6

    amends = {}
    for a in amendments:
        amends[a.label_id] = a.content

    for l in ['200-1-i', '200-1', '200-2', '200-3-a', '200-3', '200']:
        assert l in amends

    for label, node in amends.items():
        assert label == '-'.join(node['node']['label'])
        assert node['action'] == 'POST'
        assert 'children' not in node['node']


def test_create_add_amendment_parent_label():
    """If an amendment has an explicit parent_label, it should only be
    applied to the root of the tree"""
    root = _build_tree()
    amendment = {'node': root, 'action': 'POST',
                 'parent_label': ['arbitrary']}
    amendments = changes.create_add_amendment(amendment)
    assert len(amendments) == 6
    amends = {}
    for a in amendments:
        amends[a.label_id] = a.content

    assert amends['200'].get('parent_label') == ['arbitrary']
    for label, change in amends.items():
        if label == '200':
            assert change['parent_label'] == ['arbitrary']
        else:
            assert 'parent_label' not in change


def test_flatten_tree():
    tree = _build_tree()

    node_list = []
    changes.flatten_tree(node_list, tree)

    assert len(node_list) == 6
    for n in node_list:
        assert n.children == []


def test_resolve_candidates():
    amend_map = {}

    n1 = Node('n1', label=['200', '1'])
    amend_map['200-1-a'] = [{'node': n1, 'candidate': False}]

    n2 = Node('n2', label=['200', '2', 'i'])
    amend_map['200-2-a-i'] = [{'node': n2, 'candidate': True}]

    assert amend_map['200-2-a-i'][0]['node'].label_id() != '200-2-a-i'

    changes.resolve_candidates(amend_map)

    assert amend_map['200-2-a-i'][0]['node'].label_id() == '200-2-a-i'


def test_resolve_candidates_accounted_for():
    amend_map = {}

    n1 = Node('n1', label=['200', '1'])
    amend_map['200-1-a'] = [{'node': n1, 'candidate': False}]

    n2 = Node('n2', label=['200', '2', 'i'])

    amend_map['200-2-a-i'] = [{'node': n2, 'candidate': True}]
    amend_map['200-2-i'] = [{'node': n2, 'candidate': False}]

    changes.resolve_candidates(amend_map, warn=False)
    assert len(amend_map.keys()) == 2


def test_resolve_candidates_double_delete():
    """In the unfortunate case where *two* candidates are wrong make sure we
    don't blow up"""
    amend_map = {}

    n1 = Node('n1', label=['200', '1', 'i'])
    n2 = Node('n2', label=['200', '1', 'i'])
    amend_map['200-1-a-i'] = [{'node': n1, 'candidate': True},
                              {'node': n2, 'candidate': True}]
    amend_map['200-1-i'] = []
    changes.resolve_candidates(amend_map, warn=False)
    assert len(amend_map.keys()) == 1


def test_match_labels_and_changes_move():
    labels_amended = [Amendment('MOVE', '200-?-1', '200-?-2')]
    amend_map = changes.match_labels_and_changes(labels_amended, None)
    assert dict(amend_map) == {
        '200-1': [{'action': 'MOVE', 'destination': ['200', '2'],
                   'amdpar_xml': None}]
    }


def test_match_labels_and_changes_delete():
    labels_amended = [Amendment('DELETE', '200-?-1-a-i')]
    amend_map = changes.match_labels_and_changes(labels_amended, None)
    assert dict(amend_map) == {
        '200-1-a-i': [{'action': 'DELETE', 'amdpar_xml': None}]
    }


def _section_node():
    n1 = Node('n2', label=['200', '2'])
    n2 = Node('n2a', label=['200', '2', 'a'])

    n1.children = [n2]
    root = Node('root', label=['200'], children=[n1])
    return root


def test_match_labels_and_changes_reserve():
    labels_amended = [Amendment('RESERVE', '200-?-2-a')]
    amend_map = changes.match_labels_and_changes(
        labels_amended, _section_node())
    assert set(amend_map.keys()) == {'200-2-a'}

    amendments = amend_map['200-2-a']
    assert amendments[0]['action'] == 'RESERVE'
    assert amendments[0]['node'] == Node('n2a', label=['200', '2', 'a'])


def test_match_labels_and_changes():
    labels_amended = [Amendment('POST', '200-?-2'),
                      Amendment('PUT', '200-?-2-a')]

    amend_map = changes.match_labels_and_changes(
        labels_amended, _section_node())

    assert len(amend_map) == 2

    for amendments in amend_map.values():
        amend = amendments[0]
        assert not amend['candidate']
        assert amend['action'] in ('POST', 'PUT')


def test_match_labels_and_changes_candidate():
    labels_amended = [
        Amendment('POST', '200-?-2'),
        Amendment('PUT', '200-?-2-a-1-i')]

    n1 = Node('n2', label=['200', '2'])
    n2 = Node('n2a', label=['200', '2', 'i'])

    n1.children = [n2]
    root = Node('root', label=['200'], children=[n1])

    amend_map = changes.match_labels_and_changes(
        labels_amended, root)

    assert amend_map['200-2-a-1-i'][0]['candidate']
    assert amend_map['200-2-a-1-i'][0]['node'].label_id() == '200-2-a-1-i'


def test_bad_label():
    label = ['205', '4', 'a', '1', 'ii', 'A']
    node = Node('text', label=label, node_type=Node.REGTEXT)
    assert not changes.bad_label(node)

    node.label = ['205', '38', 'i', 'vii', 'A']
    assert changes.bad_label(node)

    node.label = ['205', 'ii']
    assert changes.bad_label(node)

    node.label = ['205', '38', 'A', 'vii', 'A']
    assert changes.bad_label(node)


def test_impossible_label():
    amended_labels = ['205-35-c-1', '205-35-c-2']
    node = Node('', label=['205', '35', 'v'])
    assert changes.impossible_label(node, amended_labels)

    node = Node('', label=['205', '35', 'c', '1', 'i'])
    assert not changes.impossible_label(node, amended_labels)


def test_new_subpart_added():
    amended_label = Amendment('POST', '200-Subpart:B')
    assert changes.new_subpart_added(amended_label)

    amended_label = Amendment('PUT', '200-Subpart:B')
    assert not changes.new_subpart_added(amended_label)

    amended_label = Amendment('POST', '200-Subpart:B-a-3')
    assert not changes.new_subpart_added(amended_label)


def test_find_subpart():
    with XMLBuilder("REGTEXT", PART='105', TITLE='12') as ctx:
        ctx.AMDPAR("6. Add subpart B to read as follows:")
        with ctx.SUBPART():
            ctx.HD("Subpart B—Requirements", SOURCE="HED")
            with ctx.SECTION():
                ctx.SECTNO("105.30")
                ctx.SUBJECT("First In New Subpart")
                ctx.P("For purposes of this subpart, the follow apply:")
                ctx.P('(a) "Agent" means agent.')

    amdpar_xml = ctx.xml.xpath('//AMDPAR')[0]
    subpart = changes.find_subpart(amdpar_xml)
    assert subpart is not None

    headings = [s for s in subpart if s.tag == 'HD']
    assert headings[0].text == "Subpart B—Requirements"


def test_fix_section_node():
    with XMLBuilder("REGTEXT") as ctx:
        ctx.P("paragraph 1")
        ctx.P("paragraph 2")
    paragraphs = [p for p in ctx.xml if p.tag == 'P']

    with XMLBuilder("REGTEXT") as ctx:
        with ctx.SECTION():
            ctx.SECTNO(" 205.4 ")
            ctx.SUBJECT("[Corrected]")
        ctx.AMDPAR("3. In § 105.1, revise paragraph (b) to read as follows:")
    par = ctx.xml.xpath('//AMDPAR')[0]
    section = changes.fix_section_node(paragraphs, par)
    assert section is not None
    section_paragraphs = [p for p in section if p.tag == 'P']
    assert len(section_paragraphs) == 2

    assert section_paragraphs[0].text == 'paragraph 1'
    assert section_paragraphs[1].text == 'paragraph 2'


def test_notice_changes_update_duplicates():
    nc = changes.NoticeChanges()
    nc.add_change(None, changes.Change('123-12', {'action': 'DELETE'}))
    nc.add_change(None, changes.Change('123-22', {'action': 'OTHER'}))
    nc.add_change(None, changes.Change('123-12', {'action': 'DELETE'}))
    nc.add_change(None, changes.Change('123-12', {'action': 'OTHER'}))
    nc.add_change(None, changes.Change('123-22', {'action': 'OTHER'}))
    nc.add_change(None, changes.Change('123-32', {'action': 'LAST'}))

    data = nc[None]
    assert '123-12' in data
    assert '123-22' in data
    assert '123-32' in data

    assert data['123-12'] == [{'action': 'DELETE'}, {'action': 'OTHER'}]
    assert data['123-22'] == [{'action': 'OTHER'}]
    assert data['123-32'] == [{'action': 'LAST'}]


def test_create_subpart_amendment():
    """We expect the sections to include a parent_label, but not the
    paragraphs"""
    subpart = Node(
        label=['111', 'Subpart', 'C'], node_type=Node.SUBPART, children=[
            Node(label=['111', '22'],
                 children=[Node(label=['111', '22', 'a']),
                           Node(label=['111', '22', 'b'])]),
            Node(label=['111', '23'])
        ])
    results = changes.create_subpart_amendment(subpart)
    results = list(sorted(results, key=lambda r: r.label_id))

    def empty_node(label, node_type='regtext'):
        return dict(text='', tagged_text='', title=None, node_type=node_type,
                    child_labels=[], label=label)

    assert results == [
        changes.Change('111-22', dict(parent_label=['111', 'Subpart', 'C'],
                                      action='POST',
                                      node=empty_node(['111', '22']))),
        changes.Change('111-22-a', dict(action='POST',
                                        node=empty_node(['111', '22', 'a']))),
        changes.Change('111-22-b', dict(action='POST',
                                        node=empty_node(['111', '22', 'b']))),
        changes.Change('111-23', dict(parent_label=['111', 'Subpart', 'C'],
                                      action='POST',
                                      node=empty_node(['111', '23']))),
        changes.Change(
            '111-Subpart-C',
            dict(action='POST',
                 node=empty_node(['111', 'Subpart', 'C'], 'subpart'))),
    ]
