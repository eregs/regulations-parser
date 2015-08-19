# vim: set encoding=utf-8
import unittest

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

    def test_get_paragraph_marker(self):
        text = '(k)(2)(iii) abc (j)'
        result = [m for m in tree_utils.get_paragraph_markers(text)]
        self.assertEqual(['k', '2', 'iii'], result)

        text = '(i)(A) The minimum period payment'
        result = [m for m in tree_utils.get_paragraph_markers(text)]
        self.assertEqual(['i', 'A'], result)

    def test_get_node_text_tags(self):
        text = '<P>(a)<E T="03">Fruit.</E>Apples,<PRTPAGE P="102"/> and '
        text += 'Pineapples</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text_tags_preserved(doc)

        self.assertEquals(
            '(a)<E T="03">Fruit.</E>Apples, and Pineapples', result)

    def test_no_tags(self):
        text = '<P>(a) Fruit. Apples, and Pineapples</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text_tags_preserved(doc)
        self.assertEqual('(a) Fruit. Apples, and Pineapples', result)

    def test_get_node_text(self):
        text = '<P>(a)<E T="03">Fruit.</E>Apps,<PRTPAGE P="102"/> and pins</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text(doc)

        self.assertEquals('(a)Fruit.Apps, and pins', result)

        text = '<P>(a)<E T="03">Fruit.</E>Apps,<PRTPAGE P="102"/> and pins</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text(doc, add_spaces=True)

        self.assertEquals('(a) Fruit. Apps, and pins', result)

        text = '<P>(a) <E T="03">Fruit.</E> Apps, and pins</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text(doc, add_spaces=True)

        self.assertEquals('(a) Fruit. Apps, and pins', result)

        text = '<P>(a) ABC<E T="52">123</E>= 5</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text(doc, add_spaces=True)
        self.assertEquals('(a) ABC_{123} = 5', result)

        text = '<P>(a) <E>Keyterm.</E> ABC<E T="52">123</E>= 5</P>'
        doc = etree.fromstring(text)
        result = tree_utils.get_node_text(doc, add_spaces=True)
        self.assertEquals('(a) Keyterm. ABC_{123} = 5', result)

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

    def test_get_collapsed_markers(self):
        text = u'(a) <E T="03">Transfer </E>—(1) <E T="03">Notice.</E> follow'
        markers = tree_utils.get_collapsed_markers(text)
        self.assertEqual(markers, [u'1'])

        text = '(1) See paragraph (a) for more'
        self.assertEqual([], tree_utils.get_collapsed_markers(text))

        text = '(a) (1) More content'
        self.assertEqual([], tree_utils.get_collapsed_markers(text))

        text = u'(a) <E T="03">Transfer—</E>(1) <E T="03">Notice.</E> follow'
        self.assertEqual([u'1'], tree_utils.get_collapsed_markers(text))

        text = u'(a) <E T="03">Keyterm</E>—(1)(i) Content'
        self.assertEqual(['1', 'i'], tree_utils.get_collapsed_markers(text))

        text = "(C) The information required by paragraphs (a)(2), "
        text += "(a)(4)(iii), (a)(5), (b) through (d), (i), (l) through (p)"
        self.assertEqual([], tree_utils.get_collapsed_markers(text))
