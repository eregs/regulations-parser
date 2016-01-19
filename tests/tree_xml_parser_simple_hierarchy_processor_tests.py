from unittest import TestCase

from regparser.tree.xml_parser.simple_hierarchy_processor import (
        SimpleHierarchyMatcher)
from tests.xml_builder import XMLBuilderMixin
from tests.node_accessor import NodeAccessorMixin


class SimpleHierarchyTests(XMLBuilderMixin, NodeAccessorMixin, TestCase):
    def test_deep_hierarchy(self):
        """Run through a full example, converting an XML node into an
        appropriate tree of nodes"""
        with self.tree.builder("ROOT") as root:
            root.P("(a) AAA")
            root.P("(b) BBB")
            root.P("i. BIBIBI")
            root.P("ii. BIIBIIBII")
            root.P("(1) BII1BII1BII1")
            root.P("(2) BII2BII2BII2")
            root.P("iii. BIIIBIIIBIII")
            root.P("(c) CCC")

        matcher = SimpleHierarchyMatcher(['ROOT'], 'some_type')
        nodes = matcher.derive_nodes(self.tree.render_xml())
        self.assertEqual(1, len(nodes))

        node = self.node_accessor(nodes[0], nodes[0].label)
        self.assertEqual('some_type', node.node_type)
        self.assertEqual(['a', 'b', 'c'], node.child_labels)
        self.assertNotEqual('some_type', node['a'].node_type)
        self.assertEqual(node['a'].text, '(a) AAA')
        self.assertEqual([], node['a'].child_labels)
        self.assertEqual(node['c'].text, '(c) CCC')
        self.assertEqual([], node['c'].child_labels)

        self.assertEqual(node['b'].text, '(b) BBB')
        self.assertEqual(['i', 'ii', 'iii'], node['b'].child_labels)
        self.assertEqual(node['b']['i'].text, 'i. BIBIBI')
        self.assertEqual([], node['b']['i'].child_labels)
        self.assertEqual(node['b']['iii'].text, 'iii. BIIIBIIIBIII')
        self.assertEqual([], node['b']['iii'].child_labels)

        self.assertEqual(node['b']['ii'].text, 'ii. BIIBIIBII')
        self.assertEqual(['1', '2'], node['b']['ii'].child_labels)
        self.assertEqual(node['b']['ii']['1'].text, '(1) BII1BII1BII1')
        self.assertEqual([], node['b']['ii']['1'].child_labels)
        self.assertEqual(node['b']['ii']['2'].text, '(2) BII2BII2BII2')
        self.assertEqual([], node['b']['ii']['2'].child_labels)

    def test_no_children(self):
        """Elements with only one, markerless paragraph should not have
        children"""
        with self.tree.builder("NOTE") as root:
            root.P("Some text here")

        matcher = SimpleHierarchyMatcher(['NOTE'], 'note')
        nodes = matcher.derive_nodes(self.tree.render_xml())
        self.assertEqual(1, len(nodes))
        node = nodes[0]

        self.assertEqual('note', node.node_type)
        self.assertEqual('Some text here', node.text)
        self.assertEqual([], node.children)
