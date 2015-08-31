#vim: set encoding=utf-8
from unittest import TestCase

from regparser.grammar.terms import *

def parse_text(text):
    return [m[0] for m, _, _ in token_patterns.scanString(text)]

class GrammarTermsTests(TestCase):

    def test_xml_term_parser(self):
        text = u'(1) <E T="03">Damages incurred</E> means actual damages incurred'
        result = [match for match, _, _ in xml_term_parser.scanString(text)]
        match = result[0]
        self.assertEqual(len(result), 1)
        self.assertEqual(match.term[0], 'Damages')
        self.assertEqual(match.term[1], 'incurred')

        text = u'<E T="03">Damages incurred</E> means actual damages incurred'
        result = [match for match, _, _ in xml_term_parser.scanString(text)]
        match = result[0]
        self.assertEqual(len(result), 1)
        self.assertEqual(match.term[0], 'Damages')
        self.assertEqual(match.term[1], 'incurred')

        # This sort of text shouldn't match.
        text = u"This sort of text shouldn't match."
        result = [match for match, _, _ in xml_term_parser.scanString(text)]
        self.assertEqual(len(result), 0)

    def test_comma_clauses(self):
        text = u'(v) <E T="03">Negative factor or value</E>, in relation to the age of elderly applicants, means utilizing a factor, value, or weight'
        result = [match for match, _, _ in xml_term_parser.scanString(text)]
        match = result[0]
        self.assertEqual(len(result), 1)
        self.assertEqual(match.term[0], 'Negative')
        self.assertEqual(match.term[1], 'factor')
        self.assertEqual(match.term[2], 'or')
        self.assertEqual(match.term[3], 'value')

