# vim: set encoding=utf-8
from regparser.citations import Label
from regparser.tree import interpretation
from unittest import TestCase


class DepthInterpretationTreeTest(TestCase):
    def test_text_to_labels(self):
        text = u"9(c)(2)(iii) Charges not Covered by § 1026.6(b)(1) and "
        text += "(b)(2)"
        self.assertEqual(
            [['1111', '9', 'c', '2', 'iii', 'Interp']],
            interpretation.text_to_labels(text,
                                          Label(part='1111', comment=True)))

        text = "Paragraphs 4(b)(7) and (b)(8)."
        self.assertEqual(
            [['1111', '4', 'b', '7', 'Interp'],
             ['1111', '4', 'b', '8', 'Interp']],
            interpretation.text_to_labels(text,
                                          Label(part='1111', comment=True)))

        text = "Appendices G and H-Something"
        self.assertEqual(
            [['1111', 'G', 'Interp'], ['1111', 'H', 'Interp']],
            interpretation.text_to_labels(text,
                                          Label(part='1111', comment=True)))

        text = "Paragraph 38(l)(7)(i)(A)(2)."
        self.assertEqual(
            [['1111', '38', 'l', '7', 'i', 'A', '2', 'Interp']],
            interpretation.text_to_labels(text,
                                          Label(part='1111', comment=True)))

    def test_merge_labels(self):
        labels = [['1021', 'A'], ['1021', 'B']]
        self.assertEqual(['1021', 'A_B'], interpretation.merge_labels(labels))

        labels = [['1021', 'A', '1'], ['1021', 'A', '2']]
        self.assertEqual(['1021', 'A', '1_2'],
                         interpretation.merge_labels(labels))
