# vim: set encoding=utf-8
from unittest import TestCase

from regparser.diff import tree as difftree
from regparser.tree.struct import FrozenNode


class DiffTreeTest(TestCase):
    def test_subparts(self):
        """ Create a tree with no subparts, then add subparts. """
        old_tree = FrozenNode(title="Regulation Title", label=['204'],
                              children=[
            FrozenNode(node_type='emptypart', label=['204', 'Subpart'],
                       children=[
                FrozenNode(title=u"§ 204.1 First Section", label=['204', '1'],
                           children=[
                    FrozenNode(text="(a) I believe this is the best section",
                               label=['204', '1', 'a'])]),
                FrozenNode(title=u"§ 204.2 Second Section", label=['204', '2'],
                           text=u"Some sections \ndon't have \ndepth at all.")
            ])])
        new_tree = FrozenNode(title="Regulation Title", label=['204'],
                              children=[
            FrozenNode(node_type='subpart', label=['204', 'Subpart', 'A'],
                       title=u"Subpart A—First subpart", children=[
                FrozenNode(title=u"§ 204.1 First Section", label=['204', '1'],
                           children=[
                    FrozenNode(text="(a) I believe this is the best section",
                               label=['204', '1', 'a'])])]),
            FrozenNode(node_type='subpart', label=['204', 'Subpart', 'B'],
                       title=u"Subpart B—Second subpart", children=[
                FrozenNode(title=u"§ 204.2 Second Section", label=['204', '2'],
                           text=u"Some sections \ndon't have \ndepth at all.")
            ])])

        result = dict(difftree.changes_between(old_tree, new_tree))

        self.assertEquals(
            result['204-Subpart-A'],
            {"node": {
                "text": u"", "node_type": u"subpart",
                "tagged_text": None,
                "label": ("204", "Subpart", "A"),
                "child_labels": ("204-1",),
                "title": u"Subpart A—First subpart"},
                "op": "added"})
        self.assertTrue('204-Subpart-B' in result)
        self.assertEquals(result['204-Subpart'], {"op": "deleted"})
        # Sections shouldn't have changed, though
        self.assertFalse('204-1' in result)
        self.assertFalse('204-2' in result)

    def test_title_disappears(self):
        lhs = FrozenNode("Text", title="Some Title", label=['1111'])
        rhs = FrozenNode("Text", title=None, label=['1111'])

        result = dict(difftree.changes_between(lhs, rhs))
        self.assertEqual(
            result['1111'],
            {'title': [('delete', 0, 10)], 'op': 'modified'})

    def test_child_order(self):
        """We should include child_ops if the order of children changed"""
        lhs = FrozenNode("Root", label=['1111'], children=[
            FrozenNode("Child1", label=['1111', 'a']),
            FrozenNode("Child2", label=['1111', 'b'])])
        rhs = lhs.clone(children=list(reversed(lhs.children)))
        result = dict(difftree.changes_between(lhs, rhs))
        self.assertEqual(
            result['1111'],
            # Note that these ops could change in other versions of difflib.
            {'op': 'modified', 'child_ops': [('insert', 0, ('1111-b',)),
                                             ('equal', 0, 1),  # 1111-a
                                             ('delete', 1, 2)]})

    def test_child_added(self):
        """We should include child_ops if children were added"""
        lhs = FrozenNode("Root", label=['1111'], children=[
            FrozenNode("Child1", label=['1111', 'a'])])
        new_child = FrozenNode("Child2", label=['1111', 'b'])
        rhs = lhs.clone(children=lhs.children + (new_child,))
        result = dict(difftree.changes_between(lhs, rhs))
        self.assertEqual(
            result['1111'],
            {'op': 'modified', 'child_ops': [('equal', 0, 1),   # 1111-a
                                             ('insert', 1, ('1111-b',))]})

    def test_child_removed_with_edit(self):
        """We should include child_ops if children were modified and the
        parent's text was modified"""
        lhs = FrozenNode("Root", label=['1111'], children=[
            FrozenNode("Child1", label=['1111', 'a']),
            FrozenNode("Child2", label=['1111', 'b'])])
        rhs = lhs.clone(children=lhs.children[:1], text="Root modified")
        result = dict(difftree.changes_between(lhs, rhs))
        self.assertEqual(
            result['1111'],
            {'op': 'modified',
             'text': [('insert', len("Root"), " modified")],
             'child_ops': [('equal', 0, 1),   # 1111-a
                           ('delete', 1, 2)]})

    def test_whitespace_comparison(self):
        """We shouldn't trigger diffs for whitespace changes"""
        lhs = FrozenNode(u"Some\t\nthing", label=['123'])
        rhs = lhs.clone(text=u"Some\u2009 thing")   # thin-space
        self.assertEqual(difftree.changes_between(lhs, rhs), [])
