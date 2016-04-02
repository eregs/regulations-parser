from unittest import TestCase

from regparser.notice import preamble
from regparser.notice.xml import NoticeXML
from regparser.test_utils.node_accessor import NodeAccessor
from regparser.test_utils.xml_builder import XMLBuilder


class NoticePreambleTests(TestCase):
    def test_parse_preamble_integration(self):
        """End-to-end test for parsing a notice preamble"""
        with XMLBuilder("ROOT") as ctx:
            ctx.P("ignored content")
            with ctx.SUPLINF():
                ctx.HED("Supp Inf")
                ctx.P("P1")
                ctx.P("P2")
                ctx.HD("I. H1", SOURCE="HD1")
                ctx.P("H1-P1")
                ctx.HD("A. H1-1", SOURCE="HD2")
                ctx.P("H1-1-P1")
                ctx.P("H1-1-P2")
                ctx.HD("B. H1-2", SOURCE="HD2")
                ctx.P("H1-2-P1")
                ctx.HD("II. H2", SOURCE="HD1")
                ctx.P("H2-P1")
                ctx.P("H2-P2")
                with ctx.GPH():
                    ctx.GID("111-222-333")
                ctx.LSTSUB()
                ctx.P("ignored")
            ctx.P("tail also ignored")
        xml = NoticeXML(ctx.xml)
        xml.version_id = 'vvv-yyy'
        root = NodeAccessor(preamble.parse_preamble(xml))

        self.assertEqual(root.label, ['vvv_yyy'])
        self.assertEqual(root.title, 'Supp Inf')
        self.assertEqual(root['p1'].text, 'P1')
        self.assertEqual(root['p2'].text, 'P2')
        self.assertEqual(root['I'].title, 'I. H1')
        self.assertEqual(root['I'].text, 'H1-P1')   # becomes intro
        self.assertEqual(root['I']['A'].title, 'A. H1-1')
        self.assertEqual(root['I']['A']['p1'].text, 'H1-1-P1')
        self.assertEqual(root['I']['A']['p2'].text, 'H1-1-P2')
        self.assertEqual(root['I']['B'].title, 'B. H1-2')
        self.assertEqual(root['I']['B'].text, 'H1-2-P1')    # becomes intro
        self.assertEqual(root['II'].title, 'II. H2')
        self.assertEqual(root['II']['p1'].text, 'H2-P1')
        self.assertEqual(root['II']['p2'].text, 'H2-P2')
        self.assertEqual(root['II']['p3'].text, '![](111-222-333)')
