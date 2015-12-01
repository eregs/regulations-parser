# vim: set encoding=utf-8
from unittest import TestCase

from regparser.tree import reg_text
from regparser.tree.struct import FrozenNode
from regparser.diff import tree as difftree


class DiffTreeTest(TestCase):
    def test_subparts(self):
        """ Create a tree with no subparts, then add subparts. """
        title = u"Regulation Title"
        sect1_title = u"§ 204.1 First Section"
        sect1 = u"(a) I believe this is (b) the best section "
        sect2_title = u"§ 204.2 Second Section"
        sect2 = u"Some sections \ndon't have \ndepth at all."

        old_text = "\n".join([title, sect1_title, sect1, sect2_title, sect2])
        older = reg_text.build_reg_text_tree(old_text, 204)

        ntitle = u"Regulation Title"
        nsubpart_a = u"Subpart A—First subpart"
        nsect1_title = u"§ 204.1 First Section"
        nsect1 = u"(a) I believe this is (b) the best section "
        nsubpart_b = u"Subpart B—Second subpart"
        nsect2_title = u"§ 204.2 Second Section"
        nsect2 = u"Some sections \ndon't have \ndepth at all."

        new_text = "\n".join([
            ntitle, nsubpart_a, nsect1_title,
            nsect1, nsubpart_b, nsect2_title, nsect2])
        newer = reg_text.build_reg_text_tree(new_text, 204)

        result = dict(difftree.changes_between(
            FrozenNode.from_node(older), FrozenNode.from_node(newer)))

        self.assertEquals(
            result['204-Subpart-A'],
            {"node": {
                "text": u"", "node_type": u"subpart",
                "tagged_text": None,
                "label": ("204", "Subpart", "A"),
                "child_labels": ("204-1",),
                "title": u"First subpart"},
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
