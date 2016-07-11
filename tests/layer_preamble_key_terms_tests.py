from regparser.layer.preamble.key_terms import KeyTerms
from regparser.tree.struct import Node


def test_has_keyterm():
    node = Node(text='a. thing here. more more',
                tagged_text='  a. <E T="03">thing here.</E> more more')
    assert KeyTerms.keyterm_in_node(node) == 'thing here.'


def test_must_have_marker():
    node = Node(text='not found because no marker',
                tagged_text='<E T="03">not found</E> because no marker')
    assert KeyTerms.keyterm_in_node(node) is None


def test_must_be_at_beginning():
    node = Node(text='1. something else here',
                tagged_text='1. something <E T="03">else</E> here')
    assert KeyTerms.keyterm_in_node(node) is None
