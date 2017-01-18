# vim: set encoding=utf-8
import unittest
from functools import partial as mk_partial_fn

from lxml import etree

from regparser.tree.struct import Node
from regparser.tree.xml_parser import tree_utils


class TreeUtilsTest(unittest.TestCase):
    def test_split_text(self):
        text = "(A) Apples (B) Bananas (Z) Zebras"
        tokens = ['(A)', '(B)']

        result = tree_utils.split_text(text, tokens)
        expected = ['(A) Apples ', '(B) Bananas (Z) Zebras']
        self.assertEqual(expected, result)

    def test_split_text_with_prefix(self):
        """Don't wipe out the intro text, if present"""
        text = "Some content here (A) Apples (B) Bananas (Z) Zebras"
        tokens = ['(A)', '(B)']

        result = tree_utils.split_text(text, tokens)
        expected = ['Some content here ', '(A) Apples ',
                    '(B) Bananas (Z) Zebras']
        self.assertEqual(expected, result)

    def test_consecutive_markers(self):
        text = "(A)(2) Bananas"
        tokens = ['(A)', '(2)']

        result = tree_utils.split_text(text, tokens)
        expected = ['(A)', '(2) Bananas']
        self.assertEqual(expected, result)

    def assert_transform_equality(self, input_val, expected_output, *fns):
        """Verify that the result of chaining (more specifically, composing)
        the fns on the input_val with result in the expected output value."""
        for fn in fns:
            input_val = fn(input_val)
        self.assertEqual(input_val, expected_output)

    def test_get_node_text_tags(self):
        """Verify that the irrelevant appropriate tags are stripped for a
        handful of examples"""
        transforms = [etree.fromstring,
                      tree_utils.get_node_text_tags_preserved]
        self.assert_transform_equality(
            ('<P>(a)<E T="03">Fruit.</E>Apples,<PRTPAGE P="102"/> and '
             'Pineapples</P>'),
            '(a)<E T="03">Fruit.</E>Apples, and Pineapples', *transforms)
        self.assert_transform_equality(
            '<P>(a) Fruit. Apples, and Pineapples</P>',
            '(a) Fruit. Apples, and Pineapples', *transforms)
        self.assert_transform_equality(
            '<P>(a) <E T="01">Other</E> tags: <PIGLATIN>oof</PIGLATIN></P>',
            '(a) <E T="01">Other</E> tags: <PIGLATIN>oof</PIGLATIN>',
            *transforms)

    def test_get_node_text(self):
        """Verify that the appropriate tags are removed, and, if requested,
        spaces are added for a handful of examples"""
        no_space = [etree.fromstring, tree_utils.get_node_text]
        with_space = [etree.fromstring,
                      mk_partial_fn(tree_utils.get_node_text, add_spaces=True)]

        self.assert_transform_equality(
            '<P>(a)<E T="03">Fruit.</E>Apps,<PRTPAGE P="102"/> and pins</P>',
            '(a)Fruit.Apps, and pins', *no_space)
        self.assert_transform_equality(
            '<P>(a)<E T="03">Fruit.</E>Apps,<PRTPAGE P="102"/> and pins</P>',
            '(a) Fruit. Apps, and pins', *with_space)
        self.assert_transform_equality(
            '<P>(a) <E T="03">Fruit.</E> Apps, and pins</P>',
            '(a) Fruit. Apps, and pins', *with_space)
        self.assert_transform_equality(
            '<P>(a) ABC<E T="52">123</E>= 5</P>',
            '(a) ABC_{123} = 5', *with_space)
        self.assert_transform_equality(
            '<P>(a) <E>Keyterm.</E> ABC<E T="52">123</E>= 5</P>',
            '(a) Keyterm. ABC_{123} = 5', *with_space)
        self.assert_transform_equality(
            '<P>(d) <E T="03">Text text</E>-more stuffs</P>',
            '(d) Text text-more stuffs', *with_space)
        self.assert_transform_equality(
            '<P>(d) <E T="03">Text text-</E>more stuffs</P>',
            '(d) Text text-more stuffs', *with_space)
        self.assert_transform_equality(
            u'<P>(d) <E T="03">Text text—</E>more stuffs</P>',
            u'(d) Text text—more stuffs', *with_space)
        self.assert_transform_equality(
            u'<P>(d) <E T="03">Text text</E>—more stuffs</P>',
            u'(d) Text text—more stuffs', *with_space)
        self.assert_transform_equality(
            '<P>F<E T="52">n</E> = F<E T="52">n-1</E> + '
            'F<E T="52">n-2</E></P>',
            'F_{n} = F_{n-1} + F_{n-2}', *no_space)
        self.assert_transform_equality(
            '<P>There was an error<SU footnote="but not mine!">5</SU></P>',
            'There was an error[^5](but not mine!)', *no_space)
        self.assert_transform_equality(
            '<P>Note<SU footnote="(parens), see">note</SU> that</P>',
            r'Note[^note](\(parens\), see) that', *no_space)
        self.assert_transform_equality(
            '<P>y = x<E T="52">0</E> + mx<E T="51">2</E></P>',
            'y = x_{0} + mx^{2}', *no_space)
        self.assert_transform_equality(
            '<P>y = x<E T="52">0</E> + mx<SU>2</SU></P>',
            'y = x_{0} + mx^{2}', *no_space)
        self.assert_transform_equality(
            '<P>y = x<E T="54">0</E> + mx<E T="53">2</E></P>',
            'y = x_{0} + mx^{2}', *no_space)

    def test_get_node_text_no_tail(self):
        """get_node_text should not include any "tail" present (e.g. if
        processing part of a larger XML doc)"""
        xml = etree.fromstring("<root>Some <p>paragraph</p> w/ tail</root>")
        xml = xml.xpath("./p")[0]
        self.assertEqual(tree_utils.get_node_text(xml), 'paragraph')

    def test_unwind_stack(self):
        level_one_n = Node(label=['272'])
        level_two_n = Node(label=['a'])

        m_stack = tree_utils.NodeStack()
        m_stack.push_last((1, level_one_n))
        m_stack.add(2, level_two_n)

        self.assertEquals(m_stack.size(), 2)
        m_stack.unwind()

        self.assertEquals(m_stack.size(), 1)

        n = m_stack.pop()[0][1]
        self.assertEqual(n.children[0].label, ['272', 'a'])

    def test_collapse_stack(self):
        """collapse() is a helper method which wraps up all of the node
        stack's nodes with a bow"""
        m_stack = tree_utils.NodeStack()
        m_stack.add(0, Node(label=['272']))
        m_stack.add(1, Node(label=['11']))
        m_stack.add(2, Node(label=['a']))
        m_stack.add(3, Node(label=['1']))
        m_stack.add(3, Node(label=['2']))
        m_stack.add(2, Node(label=['b']))

        reg = m_stack.collapse()
        self.assertEqual(reg.label, ['272'])
        self.assertEqual(len(reg.children), 1)

        section = reg.children[0]
        self.assertEqual(section.label, ['272', '11'])
        self.assertEqual(len(section.children), 2)

        a, b = section.children
        self.assertEqual(b.label, ['272', '11', 'b'])
        self.assertEqual(len(b.children), 0)
        self.assertEqual(a.label, ['272', '11', 'a'])
        self.assertEqual(len(a.children), 2)

        a1, a2 = a.children
        self.assertEqual(a1.label, ['272', '11', 'a', '1'])
        self.assertEqual(len(a1.children), 0)
        self.assertEqual(a2.label, ['272', '11', 'a', '2'])
        self.assertEqual(len(a2.children), 0)
