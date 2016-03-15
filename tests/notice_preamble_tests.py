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
                suplinf.HD("H1", SOURCE="HD1")
                suplinf.P("H1-P1")
                suplinf.HD("H1-1", SOURCE="HD2")
                suplinf.P("H1-1-P1")
                suplinf.P("H1-1-P2")
                suplinf.HD("H1-2", SOURCE="HD2")
                suplinf.P("H1-2-P1")
                suplinf.HD("H2", SOURCE="HD1")
                suplinf.P("H2-P1")
                suplinf.P("H2-P2")
                suplinf.LSTSUB()
                suplinf.P("ignored")
            root.P("tail also ignored")
        xml = NoticeXML(self.tree.render_xml())
        xml.version_id = 'vvv-yyy'
        root = self.node_accessor(preamble.parse_preamble(xml), ['vvv_yyy'])

        self.assertEqual(root.title, 'Supp Inf')
        self.assertEqual(root['p0'].text, 'P1')
        self.assertEqual(root['p1'].text, 'P2')
        self.assertEqual(root['p2'].title, 'H1')
        self.assertEqual(root['p2']['p0'].text, 'H1-P1')
        self.assertEqual(root['p2']['p1'].title, 'H1-1')
        self.assertEqual(root['p2']['p1']['p0'].text, 'H1-1-P1')
        self.assertEqual(root['p2']['p1']['p1'].text, 'H1-1-P2')
        self.assertEqual(root['p2']['p2'].title, 'H1-2')
        self.assertEqual(root['p2']['p2']['p0'].text, 'H1-2-P1')
        self.assertEqual(root['p3'].title, 'H2')
        self.assertEqual(root['p3']['p0'].text, 'H2-P1')
        self.assertEqual(root['p3']['p1'].text, 'H2-P2')
