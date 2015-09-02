# vim: set fileencoding=utf-8
from regparser.layer import def_finders
from regparser.layer.terms import ParentStack
from regparser.tree.struct import Node

from unittest import TestCase


class SmartQuotesTest(TestCase):
    def setUp(self):
        self.stack = ParentStack()
        self.finder = def_finders.SmartQuotes(self.stack)
        self.depth = 0

    def check_indicator(self, expected, text, title=None):
        """Common pattern for adding a node to the stack and then verifying
        the `has_def_indicator` method"""
        self.stack.add(self.depth, Node(text, title=title))
        self.assertEqual(self.finder.has_def_indicator(), expected)
        self.depth += 1

    def pop_and_check(self, expected=False):
        """Common pattern for popping the stack and then verifying the
        `has_def_indicator` method"""
        self.stack.pop()
        self.assertEqual(self.finder.has_def_indicator(), expected)
        self.depth -= 1

    def test_has_def_indicator(self):
        self.check_indicator(False, "This has no defs")
        self.check_indicator(False, "No Def", title="No def")
        self.check_indicator(
            False, "Tomatoes do not meet the definition 'vegetable'")
        self.check_indicator(True, "Definition. This has a definition.")
        self.pop_and_check()
        self.check_indicator(True, "Definitions. This has multiple!")
        self.pop_and_check()
        self.check_indicator(True, "No body",
                             title="But Definition is in the title")

    def test_has_def_indicator_p_marker(self):
        self.check_indicator(
            True,
            "(a) Definitions. For purposes of this section except blah")

    def test_has_def_indicator_the_term_means(self):
        self.check_indicator(False, 'Contains no terms or definitions')
        self.check_indicator(True, "(a) The term Bob means awesome")
        self.check_indicator(True, "No defs either")

        self.pop_and_check(expected=True)
        self.pop_and_check()
        self.check_indicator(True, u"(a) “Term” means some stuff")

        self.pop_and_check()
        self.check_indicator(True, "(a) The term Bob refers to")
