from regparser.tree.appendix import tree
from unittest import TestCase


class DepthAppendixTreeTest(TestCase):
    def test_letter_for(self):
        self.assertEqual('a', tree.letter_for(0))
        self.assertEqual('z', tree.letter_for(25))
        self.assertEqual('aa', tree.letter_for(26))
        self.assertEqual('ab', tree.letter_for(27))
        self.assertEqual('ba', tree.letter_for(52))
        #  We have 27 sets of letters; 1 with 1 character each, 26 with 2
        self.assertEqual('zz', tree.letter_for(26*27-1))
