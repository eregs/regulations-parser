from interpparser.layers import Interpretations
from regparser.tree.struct import Node


def test_process():
    root = Node(children=[
        Node("Interp11a",
             [Node("child1"), Node("child2")],
             ['102', '11', 'a', Node.INTERP_MARK],
             node_type=Node.INTERP),
        Node("Interp11c5v",
             label=['102', '11', 'c', '5', 'v', Node.INTERP_MARK],
             node_type=Node.INTERP),
        Node("InterpB5ii",
             label=['102', 'B', '5', 'ii', Node.INTERP_MARK],
             node_type=Node.INTERP),
        Node(children=[
            Node(label=['102'], children=[
                Node("Interp9c1",
                     label=['102', '9', 'c', '1', Node.INTERP_MARK],
                     node_type=Node.INTERP)
            ])
        ])
    ])

    interp = Interpretations(root)
    interp.pre_process()
    interp11a = interp.process(Node(label=['102', '11', 'a']))
    interp11c5v = interp.process(Node(
        label=['102', '11', 'c', '5', 'v']
    ))
    interpb5ii = interp.process(Node(label=['102', 'B', '5', 'ii']))
    interp9c1 = interp.process(Node(label=['102', '9', 'c', '1']))

    assert len(interp11a) == 1
    assert len(interp11c5v) == 1
    assert len(interpb5ii) == 1
    assert len(interp9c1) == 1
    assert interp11a[0]['reference'] == '102-11-a-Interp'
    assert interp11c5v[0]['reference'] == '102-11-c-5-v-Interp'
    assert interpb5ii[0]['reference'] == '102-B-5-ii-Interp'
    assert interp9c1[0]['reference'] == '102-9-c-1-Interp'
    assert interp.process(Node(label=['102', '10', 'a'])) is None


def test_process_subparagraph_of_referenced_text():
    root = Node(label=['100'], children=[
        Node("\n\n\n",
             node_type=Node.INTERP,
             label=['100', '11', 'a', Node.INTERP_MARK],
             children=[Node("Interp11a1", node_type=Node.INTERP,
                            label=['100', '11', 'a', '1', Node.INTERP_MARK])])
    ])
    interp = Interpretations(root)
    interp.pre_process()
    assert interp.process(Node(label=['100', '11', 'a'])) is None
    assert interp.process(Node(label=['100', '11', 'a', '1'])) is not None


def test_process_has_multiple_paragraphs():
    root = Node(label=['100'], children=[
        Node("\n\n\n",
             node_type=Node.INTERP,
             label=['100', '11', 'a', Node.INTERP_MARK],
             children=[Node("Interp11a-1", node_type=Node.INTERP,
                            label=['100', '11', 'a', Node.INTERP_MARK, '1'])])
    ])
    interp = Interpretations(root)
    interp.pre_process()
    assert interp.process(Node(label=['100', '11', 'a'])) is not None


def test_process_applies_to_multiple():
    i1a = Node('Text', title='Paragraph 1(a) and 1(b)', node_type=Node.INTERP,
               label=['100', '1', 'a', Node.INTERP_MARK])
    i1 = Node(label=['100', '1', Node.INTERP_MARK], node_type=Node.INTERP,
              children=[i1a])
    root = Node(label=['100', Node.INTERP_MARK], node_type=Node.INTERP,
                children=[i1])
    interp = Interpretations(root)
    interp.pre_process()
    assert interp.process(Node(label=['100', '1', 'a'])) is not None
    assert interp.process(Node(label=['100', '1', 'b'])) is not None


def test_process_regressions():
    i1a = Node('Text', title='Paragraph 1(a) and 1(b)',
               label=['100', '1', 'a', Node.INTERP_MARK])
    interp = Interpretations(i1a)
    interp.pre_process()
    assert interp.process(Node(label=['100', '1', 'a'])) is None

    i1a1 = Node('Text', title='Paragraph 1(a) and 1(b)',
                label=['100', '1', 'a', Node.INTERP_MARK, '1'],
                node_type=Node.INTERP)
    interp = Interpretations(i1a1)
    interp.pre_process()
    assert interp.process(Node(label=['100', '1', 'a'])) is None


def test_empty_interpretations():
    interp = Interpretations(None)
    assert interp.empty_interpretation(Node('\n\n'))
    assert interp.empty_interpretation(Node('', [Node('Subpar')]))
    assert not interp.empty_interpretation(Node('Content'))
    assert not interp.empty_interpretation(
        Node('', [Node('Something', label=['1', Node.INTERP_MARK, '3'])]))


def test_pre_process_multiple_interps():
    interpg = Node('GGGG', title='Appendix G',
                   label=['1111', 'G', 'Interp'], node_type=Node.INTERP)
    interph = Node('HHHH', title='Appendix H',
                   label=['1111', 'H', 'Interp'], node_type=Node.INTERP)
    interpgh = Node('GHGHGH', title='Appendices G and H',
                    label=['1111', 'G_H', 'Interp'],
                    node_type=Node.INTERP)

    tree = Node(label=['1111'], children=[
        Node(label=['1111', 'Interp'], node_type=Node.INTERP, children=[
            interpgh, interpg, interph])])

    interp = Interpretations(tree)
    interp.pre_process()

    node = Node('App G', label=['1111', 'G'], node_type=Node.APPENDIX)
    assert interp.process(node) == [{'reference': '1111-G_H-Interp'},
                                    {'reference': '1111-G-Interp'}]
