from unittest import TestCase

from mock import patch

from regparser.test_utils.node_accessor import NodeAccessor
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser import note_processor


class NoteProcessingTests(TestCase):
    def test_integration(self):
        """Verify that a NOTE tag is converted into an appropriate tree. We
        also expect no warnings to be emitted"""
        with XMLBuilder("NOTES") as ctx:
            ctx.HD("Notes:")
            ctx.P("1. 111")
            ctx.P("a. 1a1a1a")
            ctx.P("b. 1b1b1b")
            ctx.P("2. 222")

        matcher = note_processor.NoteMatcher()
        self.assertTrue(matcher.matches(ctx.xml))
        to_patch = 'regparser.tree.xml_parser.paragraph_processor.logger'
        with patch(to_patch) as logger:
            results = matcher.derive_nodes(ctx.xml)
        self.assertFalse(logger.warning.called)

        self.assertEqual(len(results), 1)
        tree = NodeAccessor(results[0])
        self.assertEqual(tree['1'].text, '1. 111')
        self.assertEqual(tree['1']['a'].text, 'a. 1a1a1a')
        self.assertEqual(tree['1']['b'].text, 'b. 1b1b1b')
        self.assertEqual(tree['2'].text, '2. 222')
