# vim: set fileencoding=utf-8
import re
from unittest import TestCase

from regparser.layer import def_finders
from regparser.layer.scope_finder import ScopeFinder
from regparser.layer.terms import ParentStack
from regparser.tree.struct import Node


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

    def assert_finds_definition(self, text, *expected):
        """Check that the definition is _not_ found when it has no
        "Definition" parent and _is_ found when such a parent exists"""
        self.stack.add(0, Node(label=['999']))
        node = Node(text)
        self.assertEqual([], self.finder.find(node))

        self.stack.add(1, Node("Definitions", label=['999', '1']))
        actual = self.finder.find(node)
        self.assertEqual(len(expected), len(actual))
        for expected_ref, actual_ref in zip(expected, actual):
            self.assertEqual(expected_ref.term, actual_ref.term)
            self.assertEqual(expected_ref.start, actual_ref.start)

        self.stack.pop()

    def test_find(self):
        """Tests several examples involving smart quotes"""
        self.assert_finds_definition(
            u'This has a “worD” and then more',
            def_finders.Ref('word', None, 12))
        self.assert_finds_definition(
            u'I have “anotheR word” term and “moree”',
            def_finders.Ref('another word', None, 8),
            def_finders.Ref('moree', None, 32))
        self.assert_finds_definition(
            u'But the child “DoeS sEe”?',
            def_finders.Ref('does see', None, 15))
        self.assert_finds_definition(
            u'Start with “this,”', def_finders.Ref('this', None, 12))
        self.assert_finds_definition(
            u'Start with “this;”', def_finders.Ref('this', None, 12))
        self.assert_finds_definition(
            u'Start with “this.”', def_finders.Ref('this', None, 12))
        self.assert_finds_definition(
            u'As do “subchildren”', def_finders.Ref('subchildren', None, 7))


class XMLTermMeansTest(TestCase):
    def assert_finds_result(self, tagged_text, term, start):
        """Check that the definition is found and matches the position"""
        self._assert_finds(tagged_text, def_finders.Ref(term, None, start))

    def assert_finds_no_result(self, tagged_text):
        self._assert_finds(tagged_text)   # no references

    def _assert_finds(self, tagged_text, *refs):
        """Compare the derived results to an expected number of references"""
        finder = def_finders.XMLTermMeans()
        text = re.sub(r"<[^>]*>", "", tagged_text)  # removes tags
        node = Node(text)
        node.tagged_text = tagged_text
        actual = finder.find(node)
        self.assertEqual(len(refs), len(actual))
        for ref, actual in zip(refs, actual):
            self.assertEqual(ref.term, actual.term)
            self.assertEqual(ref.start, actual.start)

    def test_find(self):
        """Test several examples that would result in a definition found"""
        self.assert_finds_result(
            '(4) <E T="03">Thing</E> means a thing that is defined',
            'thing', 4)
        self.assert_finds_result(
            '(e) <E T="03">Well-meaning lawyers</E> means people who do '
            'weird things',
            'well-meaning lawyers', 4)
        self.assert_finds_result(
            '(e) <E T="03">Words</E> have the same meaning as in a dictionary',
            'words', 4)
        self.assert_finds_result(
            '(e) <E T="03">Banana</E> has the same meaning as bonono',
            'banana', 4)
        self.assert_finds_result(
            '(f) <E T="03">Huge billowy clouds</E> means I want to take a nap',
            'huge billowy clouds', 4)
        self.assert_finds_result(
            '(v) <E T="03">Lawyers</E>, in relation to coders, means '
            'something very different',
            'lawyers', 4)

    def test_find_no_results(self):
        """Test several examples where we are expecting no definitions to be
        found"""
        self.assert_finds_no_result(
            '(d) <E T="03">Term1</E> or <E T="03">term2></E> means stuff')


class ScopeMatchTest(TestCase):
    def setUp(self):
        self.finder = def_finders.ScopeMatch(ScopeFinder())

    def assert_finds_result(self, text, term, start):
        """Check that the definition is found and matches the position"""
        actual = self.finder.find(Node(text))
        self.assertEqual(1, len(actual))
        actual = actual[0]
        self.assertEqual(term, actual.term)
        self.assertEqual(start, actual.start)

    def test_find(self):
        """Test several examples that would result in a definition found"""
        self.assert_finds_result(
            'For purposes of this section, the term blue means the color',
            'blue', 39)
        self.assert_finds_result(
            'For purposes of paragraph (a)(1) of this section, the term cool '
            'bro means hip cat',
            'cool bro', 59),
        self.assert_finds_result(
            'For purposes of this paragraph, po jo means "poor Joe"',
            'po jo', 32)


class DefinitionKeytermTest(TestCase):
    def assert_finds_result(self, tagged_text, parent_title, *refs):
        """Given the tags and a title for a parent node, verify that the
        provided references are found"""
        parent = Node(label=['1000', '1'], title=parent_title)
        node = Node(re.sub(r"<[^>]*>", "", tagged_text))  # removes tags
        node.tagged_text = tagged_text
        results = def_finders.DefinitionKeyterm(parent).find(node)
        self.assertEqual(len(results), len(refs))
        for expected, actual in zip(refs, results):
            self.assertEqual(expected.term, actual.term)
            self.assertEqual(expected.start, actual.start)

    def test_titles(self):
        """Validate various titles for the parent"""
        tagged_text = '<E T="03">Abc.</E> A paragraph'
        ref = def_finders.Ref('abc', None, 0)
        self.assert_finds_result(tagged_text, 'Definition.', ref)
        self.assert_finds_result(tagged_text, 'Definition', ref)
        self.assert_finds_result(tagged_text, 'Meaning of terms', ref)
        self.assert_finds_result(tagged_text, 'Meaning Of Terms?', ref)
        self.assert_finds_result(tagged_text, 'Some other defs')    # no match

    def test_find_success(self):
        """Verify that references can be found"""
        self.assert_finds_result(
            '(a) <E T="03">Definition</E>. Paragraph text', 'Definition',
            def_finders.Ref('definition', None, 4))
        self.assert_finds_result(
            '<E T="03">Another Phrase.</E>. Paragraph text', 'Definition',
            def_finders.Ref('another phrase', None, 0))
        # Comma isn't enough to split the definition
        self.assert_finds_result(
            '<E T="03">Officer, office.</E>. Paragraph text', 'Definition',
            def_finders.Ref('officer, office', None, 0))
        # "Or" should split the definition if the terms are simple
        self.assert_finds_result(
            '<E T="03">Frame or receiver.</E>. Paragraph text', 'Definition',
            def_finders.Ref('frame', None, 0),
            def_finders.Ref('receiver', None, 9))
        # "Or" should *not* split the definition if the terms are complex
        self.assert_finds_result(
            '<E T="03">Common or contract carrier</E>.', 'Definition',
            def_finders.Ref('common or contract carrier', None, 0))
