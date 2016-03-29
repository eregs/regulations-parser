# vim: set encoding=utf-8
from unittest import TestCase

from lxml import etree
from mock import patch

from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.depth import markers as mtypes
from regparser.tree.depth.derive import ParAssignment
from regparser.tree.struct import Node
from regparser.tree.xml_parser import paragraph_processor


class _ExampleProcessor(paragraph_processor.ParagraphProcessor):
    MATCHERS = [paragraph_processor.SimpleTagMatcher('TAGA'),
                paragraph_processor.SimpleTagMatcher('TAGB'),
                paragraph_processor.StarsMatcher(),
                paragraph_processor.IgnoreTagMatcher('IGNORE')]


class ParagraphProcessorTest(TestCase):
    def test_parse_nodes_matchers(self):
        """Verify that matchers are consulted per node"""
        with XMLBuilder("ROOT") as ctx:
            ctx.TAGA("Some content")
            ctx.TAGB("Some other text")
            ctx.TAGC("Not seen")
        result = _ExampleProcessor().parse_nodes(ctx.xml)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text, 'Some content')
        self.assertEqual(result[1].text, 'Some other text')
        # TAGC content is ignored as there is no matcher

    def test_parse_nodes_training_stars(self):
        """Trailing stars should be ignored"""
        with XMLBuilder("ROOT") as ctx:
            ctx.STARS()
            ctx.TAGA("Some other text")
            ctx.STARS()
        result = _ExampleProcessor().parse_nodes(ctx.xml)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].label, [mtypes.STARS_TAG])
        self.assertEqual(result[1].text, 'Some other text')

    def test_parse_nodes_node_type(self):
        """ All created nodes should have the default type, regtext, except for
        specific elements. The NODE_TYPE of the processor object is no longer
        used. """
        with XMLBuilder("ROOT") as ctx:
            ctx.TAGA("Some content")
            ctx.TAGB("Some other text")
        result = _ExampleProcessor().parse_nodes(ctx.xml)
        self.assertEqual([n.node_type for n in result], ['regtext', 'regtext'])

    def test_build_hierarchy(self):
        """Nodes should be returned at the provided depths"""
        root = Node(label=['root'])
        nodes = [Node(label=['a']), Node(label=['1']), Node(label=['2']),
                 Node(label=['i']), Node(label=['b']), Node(label=['c'])]
        depths = [ParAssignment(mtypes.lower, 0, 0),
                  ParAssignment(mtypes.ints, 0, 1),
                  ParAssignment(mtypes.ints, 1, 1),
                  ParAssignment(mtypes.roman, 0, 2),
                  ParAssignment(mtypes.lower, 1, 0),
                  ParAssignment(mtypes.lower, 2, 0)]
        result = _ExampleProcessor().build_hierarchy(root, nodes, depths)
        self.assertEqual(result.label, ['root'])
        self.assertEqual(len(result.children), 3)

        a, b, c = result.children
        self.assertEqual(a.label, ['root', 'a'])
        self.assertEqual(len(a.children), 2)
        self.assertEqual(b.label, ['root', 'b'])
        self.assertEqual(len(b.children), 0)
        self.assertEqual(c.label, ['root', 'c'])
        self.assertEqual(len(c.children), 0)

        a1, a2 = a.children
        self.assertEqual(a1.label, ['root', 'a', '1'])
        self.assertEqual(len(a1.children), 0)
        self.assertEqual(a2.label, ['root', 'a', '2'])
        self.assertEqual(len(a2.children), 1)

        self.assertEqual(a2.children[0].label, ['root', 'a', '2', 'i'])

    def test_build_hierarchy_markerless(self):
        """Markerless nodes should receive a unique designation"""
        root = Node(label=['root'])
        nodes = [Node(label=[mtypes.MARKERLESS]), Node(label=['a']),
                 Node(label=[mtypes.MARKERLESS]), Node(label=['b'])]
        depths = [ParAssignment(mtypes.markerless, 0, 0),
                  ParAssignment(mtypes.lower, 0, 1),
                  ParAssignment(mtypes.markerless, 0, 2),
                  ParAssignment(mtypes.lower, 1, 1)]
        result = _ExampleProcessor().build_hierarchy(root, nodes, depths)
        self.assertEqual(len(result.children), 1)

        p1 = result.children[0]
        self.assertEqual(p1.label, ['root', 'p1'])
        self.assertEqual(len(p1.children), 2)

        a, b = p1.children
        self.assertEqual(a.label, ['root', 'p1', 'a'])
        self.assertEqual(len(a.children), 1)
        self.assertEqual(a.children[0].label, ['root', 'p1', 'a', 'p1'])
        self.assertEqual(b.label, ['root', 'p1', 'b'])

    def test_separate_intro_empty_nodes(self):
        """ Make sure separate_intro can handle an empty node list. """
        nodes = []
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertEqual(None, intro)
        self.assertEqual(nodes[1:], rest)

    def test_separate_intro_positive(self):
        """Positive test cases for a separate introductory paragraph"""
        # The typical case:
        nodes = [Node(label=[mtypes.MARKERLESS]), Node(label=['a']),
                 Node(label=['b']), Node(label='1')]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertEqual(nodes[0], intro)
        self.assertEqual(nodes[1:], rest)

    def test_separate_intro_negative(self):
        """Negative test cases for a separate introductory paragraph"""
        # Multiple MARKERLESS nodes:
        nodes = [Node(label=[mtypes.MARKERLESS]),
                 Node(label=[mtypes.MARKERLESS]),
                 Node(label=[mtypes.MARKERLESS]),
                 Node(label=[mtypes.MARKERLESS])]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertIsNone(intro)
        self.assertEqual(nodes, rest)

    def test_separate_intro_with_title(self):
        """Paragraphs with a title shouldn't be considered intro paragraphs"""
        nodes = [Node(label=[mtypes.MARKERLESS], title='Some awesome title'),
                 Node(label=['a']), Node(label=['b']), Node(label='1')]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertIsNone(intro)
        self.assertEqual(nodes, rest)

    def test_separate_intro_with_table(self):
        """ We don't want tables to be turned into intro paragraphs. """
        # A MARKERLESS node followed by a table node:
        xml_table = etree.fromstring('<GPOTABLE>stuff</GPOTABLE>')
        table_node = Node(label=[mtypes.MARKERLESS], source_xml=xml_table)
        nodes = [Node(label=[mtypes.MARKERLESS, table_node])]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertEqual(nodes[0], intro)
        self.assertEqual(nodes[1:], rest)

        # A node containing only a table:
        xml_table = etree.fromstring('<GPOTABLE>stuff</GPOTABLE>')
        table_node = Node(label=[mtypes.MARKERLESS], source_xml=xml_table)
        nodes = [table_node]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertIsNone(intro)
        self.assertEqual(nodes, rest)

        # A table node and another node:
        nodes = [table_node, Node(label=['a'])]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertIsNone(intro)
        self.assertEqual(nodes, rest)
        nodes = [table_node, Node(label=[mtypes.MARKERLESS])]
        intro, rest = _ExampleProcessor().separate_intro(nodes)
        self.assertIsNone(intro)
        self.assertEqual(nodes, rest)

    def test_logging(self):
        """We should be writing a log when there are tags we weren't
        expecting. We should not be writing a log if those tags are explicitly
        ignored"""
        with XMLBuilder("ROOT") as ctx:
            ctx.IGNORE("this tag is explicitly ignored")
            ctx.UNKNOWN("this tag is not")
        to_patch = 'regparser.tree.xml_parser.paragraph_processor.logger'
        with patch(to_patch) as logger:
            result = _ExampleProcessor().parse_nodes(ctx.xml)
        self.assertEqual(result, [])
        self.assertEqual(logger.warning.call_count, 1)
        self.assertIn('UNKNOWN', logger.warning.call_args[0][1])
        self.assertNotIn('IGNORE', logger.warning.call_args[0][1])
