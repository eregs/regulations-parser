# -*- coding: utf-8 -*-
from unittest import TestCase

from mock import patch

from regparser.notice import amendments
from regparser.test_utils.xml_builder import XMLBuilder


class NoticeAmendmentsTest(TestCase):
    @patch('regparser.notice.amendments.process_appendix')
    def test_parse_appendix(self, process):
        with XMLBuilder("ROOT") as ctx:
            ctx.AMDPAR("1. Adding Appendix R and S")
            ctx.HD("Appendix R to Part 1234", SOURCE="HD1")
            with ctx.EXTRACT():
                ctx.P("R1")
                ctx.P("R2")
            ctx.HD("Appendix S to Part 1234", SOURCE="HD1")
            with ctx.EXTRACT():
                ctx.P("S1")
                ctx.P("S2")

        amendments.parse_appendix(ctx.xml, '1234', 'S')
        self.assertEqual(process.call_count, 1)
        extract = process.call_args[0][0]
        self.assertEqual(['Appendix S to Part 1234', 'S1', 'S2'],
                         [n.text for n in extract])

        amendments.parse_appendix(ctx.xml, '1234', 'R')
        self.assertEqual(process.call_count, 2)
        extract = process.call_args[0][0]
        self.assertEqual(['Appendix R to Part 1234', 'R1', 'R2'],
                         [n.text for n in extract])

    @patch('regparser.notice.amendments.interpretations')
    def test_parse_interp(self, interpretations):
        xmls = []
        with XMLBuilder("REGTEXT") as ctx:
            with ctx.EXTRACT():
                ctx.P("Something")
                ctx.STARS()
                ctx.HD("Supplement I")
                ctx.HD("A")
                ctx.T1("a")
                ctx.P("b")
        xmls.append(ctx.xml)

        with XMLBuilder("REGTEXT") as ctx:
            ctx.P("Something")
            ctx.STARS()
            with ctx.SUBSECT():
                ctx.HD("Supplement I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
        xmls.append(ctx.xml)

        with XMLBuilder("REGTEXT") as ctx:
            ctx.AMDPAR("1. In Supplement I to part 111, under...")
            ctx.P("Something")
            ctx.STARS()
            ctx.HD("SUPPLEMENT I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
        xmls.append(ctx.xml)

        with XMLBuilder("REGTEXT") as ctx:
            ctx.AMDPAR("1. In Supplement I to part 111, under...")
            ctx.P("Something")
            ctx.STARS()
            with ctx.APPENDIX():
                ctx.HD("SUPPLEMENT I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
            ctx.PRTPAGE()
        xmls.append(ctx.xml)

        for xml in xmls:
            amendments.parse_interp('111', xml)
            root, nodes = interpretations.parse_from_xml.call_args[0]
            self.assertEqual(root.label, ['111', 'Interp'])
            self.assertEqual(['HD', 'T1', 'P'], [n.tag for n in nodes])

    def test_parse_interp_subpart_confusion(self):
        with XMLBuilder("REGTEXT") as ctx:
            ctx.AMDPAR("1. In Supplement I to part 111, under Section 33, "
                       "paragraph 5 is added.")
            ctx.HD("Supplement I")
            with ctx.SUBPART():
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 111.33")
                    ctx.SUBJECT("Stubby Subby")
                    ctx.STARS()
                    ctx.P("5. Some Content")
        interp = amendments.parse_interp('111', ctx.xml)
        self.assertEqual(1, len(interp.children))
        c33 = interp.children[0]
        self.assertEqual(c33.label, ['111', '33', 'Interp'])
        self.assertEqual(1, len(c33.children))
        c335 = c33.children[0]
        self.assertEqual(c335.label, ['111', '33', 'Interp', '5'])
