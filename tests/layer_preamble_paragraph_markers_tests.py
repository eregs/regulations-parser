import pytest

from regparser.layer.preamble.paragraph_markers import ParagraphMarkers
from regparser.tree.struct import Node


@pytest.mark.parametrize('prefix,marker', [
    ('1.', '1.'), ('  a.', 'a.'), ('AA. 123.', 'AA.')])
def test_positive(prefix, marker):
    """Should find the marker in a string with the provided prefix"""
    node = Node(prefix + ' some sentence')
    result = ParagraphMarkers(None).process(node)
    assert result == [{'text': marker, 'locations': [0]}]


@pytest.mark.parametrize("prefix", ['a1.', '(a)', '(a.'])
def test_negative(prefix):
    """Should _not_ find a marker if it has these prefixes"""
    node = Node(prefix + ' some sentence')
    assert ParagraphMarkers(None).process(node) is None
