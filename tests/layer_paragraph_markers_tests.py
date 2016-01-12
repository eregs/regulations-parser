from unittest import TestCase

from regparser.layer.paragraph_markers import ParagraphMarkers
from regparser.tree.struct import Node


class ParagraphMarkersTest(TestCase):
    def test_process_no_results(self):
        pm = ParagraphMarkers(None)
        for text, node_type, label in (
                ('This has no paragraph', Node.REGTEXT, ['a']),
                ('(b) Different paragraph', Node.REGTEXT, ['a']),
                ('Later (a)', Node.REGTEXT, ['a']),
                ('References (a)', Node.APPENDIX, ['111', 'A', 'a']),
                ('References a.', Node.APPENDIX, ['111', 'A', 'a'])):
            node = Node(text, label=label, node_type=node_type)
            self.assertEqual(None, pm.process(node))

    def test_process_with_results(self):
        pm = ParagraphMarkers(None)
        for m, nt, l in (('(c)', Node.REGTEXT, ['c']),
                         ('(vi)', Node.REGTEXT, ['c', 'vi']),
                         ('ii.', Node.INTERP, ['ii', Node.INTERP_MARK]),
                         ('A.', Node.INTERP, ['ii', 'A', Node.INTERP_MARK]),
                         ('(a)', Node.APPENDIX, ['111', 'A', 'a']),
                         ('a.', Node.APPENDIX, ['111', 'A', 'a'])):
            expected_result = [{"text": m, "locations": [0]}]
            node = Node(m + " Paragraph", label=l, node_type=nt)
            self.assertEqual(pm.process(node), expected_result)
            # whitespace is ignored
            node.text = "\n" + node.text
            self.assertEqual(pm.process(node), expected_result)
