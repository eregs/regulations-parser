# -*- coding: utf-8 -*-
from interpparser import tree
from regparser.citations import Label


def test_text_to_labels():
    text = u"9(c)(2)(iii) Charges not Covered by § 1026.6(b)(1) and "
    text += "(b)(2)"
    result = tree.text_to_labels(text, Label(part='1111', comment=True))
    assert result == [['1111', '9', 'c', '2', 'iii', 'Interp']]

    text = "Paragraphs 4(b)(7) and (b)(8)."
    result = tree.text_to_labels(text, Label(part='1111', comment=True))
    assert result == [['1111', '4', 'b', '7', 'Interp'],
                      ['1111', '4', 'b', '8', 'Interp']]

    text = "Appendices G and H-Something"
    result = tree.text_to_labels(text, Label(part='1111', comment=True))
    assert result == [['1111', 'G', 'Interp'], ['1111', 'H', 'Interp']]

    text = "Paragraph 38(l)(7)(i)(A)(2)."
    result = tree.text_to_labels(text, Label(part='1111', comment=True))
    assert result == [['1111', '38', 'l', '7', 'i', 'A', '2', 'Interp']]


def test_merge_labels():
    labels = [['1021', 'A'], ['1021', 'B']]
    assert tree.merge_labels(labels) == ['1021', 'A_B']

    labels = [['1021', 'A', '1'], ['1021', 'A', '2']]
    assert tree.merge_labels(labels) == ['1021', 'A', '1_2']
