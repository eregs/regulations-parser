import pytest

from regparser.grammar.tokens import Paragraph


@pytest.mark.parametrize('params,paragraph', [
    (dict(part='111', section='22', paragraph='a'), ['111', None, '22', 'a']),
    (dict(is_interp=True, paragraphs=['1', 'i', 'a']),
     [None, 'Interpretations', None, '1', 'i', 'a']),
    (dict(part='222', appendix='C', section='5'), ['222', 'Appendix:C', '5']),
    (dict(subpart='E', section='9'), [None, 'Subpart:E', '9']),
    (dict(sub='random', section='other', paragraph='p'),
     [None, 'random', 'other', 'p']),
])
def test_paragraph_make(params, paragraph):
    """Converts keyword args appropriately"""
    assert Paragraph.make(**params) == Paragraph(paragraph)
