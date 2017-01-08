# vim: set fileencoding=utf-8
from unittest import TestCase

from regparser.layer.scope_finder import ScopeFinder
from regparser.layer.terms import ParentStack
from regparser.tree.struct import Node


class ScopeFinderTest(TestCase):
    def setUp(self):
        self.finder = ScopeFinder()
        self.stack = ParentStack()

    def add_nodes(self, length):
        """There's a common prefix of nodes we'll add"""
        label = ['1000', '3', 'd', '6', 'iii']
        for i in range(length):
            self.stack.add(i, Node(label=label[:i+1]))

    def assert_scope(self, *scopes):
        self.assertEqual(list(scopes), self.finder.determine_scope(self.stack))

    def test_determine_scope_default(self):
        """Defaults to the entire reg"""
        self.add_nodes(2)
        self.assert_scope(('1000',))

    def test_determine_scope_this_part(self):
        """Definitions scoped to a part also cover the interpretations for
        that part"""
        self.add_nodes(1)
        self.stack.add(1, Node('For the purposes of this part, blah blah',
                               label=['1001', '3']))
        self.assert_scope(('1001',), ('1001', Node.INTERP_MARK))

    def test_determine_scope_this_subpart(self):
        """Subpart scope gets expanded to include other sections in the same
        subpart"""
        self.finder.subpart_map = {
            'SubPart 1': ['A', '3'],
            'Other': []
        }
        self.add_nodes(2)
        self.stack.add(2, Node('For the purposes of this subpart, yada yada',
                               label=['1000', '3', 'c']))
        self.assert_scope(('1000', 'A'), ('1000', '3'),
                          ('1000', 'A', Node.INTERP_MARK),
                          ('1000', '3', Node.INTERP_MARK))

    def test_determine_scope_this_section(self):
        """Section scope can be triggered in a child paragraph"""
        self.add_nodes(2)
        self.stack.add(2, Node('For the purposes of this section, blah blah',
                               label=['1000', '3', 'd']))
        self.assert_scope(('1000', '3'), ('1000', '3', Node.INTERP_MARK))

    def test_determine_scope_this_paragraph(self):
        """Paragraph scope is tied to the paragraph that determined it.
        Previous paragraph scopes won't apply to adjacent children"""
        self.add_nodes(2)
        self.stack.add(2, Node('For the purposes of this section, blah blah',
                               label=['1000', '3', 'd']))
        self.stack.add(3, Node('For the purposes of this paragraph, blah blah',
                               label=['1000', '3', 'd', '5']))
        self.assert_scope(('1000', '3', 'd', '5'),
                          ('1000', '3', 'd', '5', Node.INTERP_MARK))

        self.stack.add(3, Node(label=['1002', '3', 'd', '6']))
        self.assert_scope(('1000', '3'), ('1000', '3', Node.INTERP_MARK))

        self.stack.add(3, Node('Blah as used in this paragraph, blah blah',
                               label=['1000', '3', 'd', '7']))
        self.assert_scope(('1000', '3', 'd', '7'),
                          ('1000', '3', 'd', '7', Node.INTERP_MARK))

    def test_determine_scope_purposes_of_specific_paragraph(self):
        self.add_nodes(4)
        self.stack.add(
            4, Node(u'For the purposes of this § 1000.3(d)(6)(i), blah',
                    label=['1000', '3', 'd', '6', 'i']))
        self.assert_scope(('1000', '3', 'd', '6', 'i'),
                          ('1000', '3', 'd', '6', 'i', Node.INTERP_MARK))

    def test_determine_scope_purposes_of_specific_section(self):
        self.add_nodes(4)
        self.stack.add(4, Node(u'For the purposes of § 1000.3, blah',
                               label=['1000', '3', 'd', '6', 'ii']))
        self.assert_scope(('1000', '3'), ('1000', '3', Node.INTERP_MARK))

    def test_determine_scope_as_used_in_thi_section(self):
        self.add_nodes(4)
        self.stack.add(4, Node('As used in this section, blah blah',
                               label=['1000', '3', 'd', '6', 'iii']))
        self.assert_scope(('1000', '3'), ('1000', '3', Node.INTERP_MARK))

    def test_subpart_scope(self):
        self.finder.subpart_map = {
            None: ['1', '2', '3'],
            'A': ['7', '5', '0'],
            'Q': ['99', 'abc', 'q']
        }
        self.assertEqual([['111', '1'], ['111', '2'], ['111', '3']],
                         self.finder.subpart_scope(['111', '3']))
        self.assertEqual([['115', '7'], ['115', '5'], ['115', '0']],
                         self.finder.subpart_scope(['115', '5']))
        self.assertEqual([['62', '99'], ['62', 'abc'], ['62', 'q']],
                         self.finder.subpart_scope(['62', 'abc']))
        self.assertEqual([], self.finder.subpart_scope(['71', 'Z']))
