from unittest import TestCase

from regparser.grammar.tokens import Paragraph


class ParagraphTests(TestCase):
    def test_constructor(self):
        """Constructor's API gives a few equivalences"""
        self.assertEqual(Paragraph(part='111', section='22', paragraph='a'),
                         Paragraph(['111', None, '22', 'a']))
        self.assertEqual(
            Paragraph(is_interp=True, paragraphs=['1', 'i', 'a']),
            Paragraph([None, 'Interpretations', None, '1', 'i', 'a']))
        self.assertEqual(Paragraph(part='222', appendix='C', section='5'),
                         Paragraph(['222', 'Appendix:C', '5']))
        self.assertEqual(Paragraph(subpart='E', section='9'),
                         Paragraph([None, 'Subpart:E', '9']))
        self.assertEqual(
            Paragraph(sub='random', section='other', paragraph='p'),
            Paragraph([None, 'random', 'other', 'p']))
