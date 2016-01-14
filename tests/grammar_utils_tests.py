from unittest import TestCase

import pyparsing

from regparser.grammar import utils


class QuickSearchableTests(TestCase):
    def _compare_search(self, grammar, text):
        quick_grammar = utils.QuickSearchable(grammar)
        self.assertEqual([str(m) for m in grammar.scanString(text)],
                         [str(m) for m in quick_grammar.scanString(text)])

    def test_finds_same(self):
        """Expect QuickSearchable to find the same stuff"""
        self._compare_search(pyparsing.Literal("the"),
                             "The the theory ThE the")
        self._compare_search(
            pyparsing.Literal("some") + pyparsing.Literal("thing"),
            "something some thing some one thing SomeThing")
        self._compare_search(
            pyparsing.WordStart() + pyparsing.Literal("the"),
            "the the theory ThE the other more")
        self._compare_search(
            pyparsing.Optional("the").setResultsName("opt") + "term",
            "some term the term The Term some the Some term")
        self._compare_search(
            pyparsing.Literal("hey") | pyparsing.Literal("you"),
            "hey there you hey you hey there here heyyo")
        self._compare_search(
            pyparsing.Suppress("you") + "there",
            "hey you there! do you see this? there is here youthere")
        self._compare_search(pyparsing.Regex(r'\d+'),
                             "this thing 123 more l337 h47p")
