from unittest import TestCase

import six

from regparser.layer.preamble.internal_citations import InternalCitations
from regparser.tree.struct import Node


class InternalCitationsTests(TestCase):
    def setUp(self):
        self.ic = InternalCitations(Node(label=['111_22']))
        cits = ['111_22', '111_22-I', '111_22-I-A', '111_22-I-A-1',
                '111_22-I-A-1-a', '111_22-I-A-1-a-i', '111_22-I-A-1-a-i-a']
        self.ic.known_citations = {tuple(cit.split('-')) for cit in cits}

    def test_process_success(self):
        """We should find text with citations"""
        text = ("XXX section I.A, XXX I.A.1 XXX I.A.1.a XXX I.A.1.a.i XXX "
                "I.A.1.a.i.a")
        results = self.ic.process(Node(text))
        results = [(r['citation'], text[r['offsets'][0][0]:r['offsets'][0][1]])
                   for r in results]
        for cit, text in results:
            self.assertEqual(cit[0], '111_22')
            self.assertEqual(cit[1:], tuple(text.split('.')))
        results = [t for _, t in results]
        six.assertCountEqual(
            self,
            results, ['I.A', 'I.A.1', 'I.A.1.a', 'I.A.1.a.i', 'I.A.1.a.i.a'])

    def test_process_unknown(self):
        """We should not find a citation if it doesn't exist in the tree"""
        self.assertIsNone(self.ic.process(Node("XXX section I.B")))
