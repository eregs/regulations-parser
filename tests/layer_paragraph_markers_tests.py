from unittest import TestCase

from regparser.layer.paragraph_markers import ParagraphMarkers, marker_of
from regparser.tree.struct import Node


class ParagraphMarkersTest(TestCase):
    def test_process_no_results(self):
        pm = ParagraphMarkers(None)
        for text, node_type, label in (
                ('This has no paragraph', Node.REGTEXT, ['a']),
                ('Later (a)', Node.REGTEXT, ['a']),
                ('References (a)', Node.APPENDIX, ['111', 'A', 'a']),
                ('References a.', Node.APPENDIX, ['111', 'A', 'a']),
                ('CFR. definition', Node.REGTEXT, ['111', '12', 'p123']),
                ('Word. definition', Node.REGTEXT, ['111', '12', 'p123'])):
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

    def test_marker_of_range(self):
        """In addition to single paragraph markers, we should account for
        cases of multiple markers being present. We've encountered this for
        "Reserved" paragraphs, but there are likely other scenarios"""
        for marker, text in (('(b) - (d)', '(b) - (d) Reserved'),
                             ('(b)-(d)', '(b)-(d) Some Words'),
                             ('b. - d.', 'b. - d. Can be ignored'),
                             ('b.-d.', 'b.-d. Has no negative numbers'),
                             ('(b)', '(b) -1.0 is negative')):
            self.assertEqual(marker, marker_of(Node(text=text, label=['b'])))
