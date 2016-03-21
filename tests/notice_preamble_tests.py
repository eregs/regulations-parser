from unittest import TestCase

from regparser.notice import preamble
from regparser.notice.xml import NoticeXML
from tests.node_accessor import NodeAccessorMixin
from tests.xml_builder import XMLBuilderMixin


class NoticePreambleTests(XMLBuilderMixin, NodeAccessorMixin, TestCase):
    def test_parse_preamble_integration(self):
        """End-to-end test for parsing a notice preamble"""
        with self.tree.builder('ROOT') as root:
            root.P("ignored content")
            with root.SUPLINF() as suplinf:
                suplinf.HED("Supp Inf")
                suplinf.P("P1")
                suplinf.P("P2")
                suplinf.HD("I. H1", SOURCE="HD1")
                suplinf.P("H1-P1")
                suplinf.HD("A. H1-1", SOURCE="HD2")
                suplinf.P("H1-1-P1")
                suplinf.P("H1-1-P2")
                suplinf.HD("B. H1-2", SOURCE="HD2")
                suplinf.P("H1-2-P1")
                suplinf.HD("II. H2", SOURCE="HD1")
                suplinf.P("H2-P1")
                suplinf.P("H2-P2")
                with suplinf.GPH() as gph:
                    gph.GID("111-222-333")
                suplinf.LSTSUB()
                suplinf.P("ignored")
            root.P("tail also ignored")
        xml = NoticeXML(self.tree.render_xml())
        xml.version_id = 'vvv-yyy'
        root = self.node_accessor(preamble.parse_preamble(xml), ['vvv_yyy'])

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
