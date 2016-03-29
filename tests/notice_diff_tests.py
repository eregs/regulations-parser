# vim: set encoding=utf-8
from unittest import TestCase

from regparser.notice import diff
from regparser.notice.amdparser import Amendment
from regparser.test_utils.xml_builder import XMLBuilder


class NoticeDiffTests(TestCase):
    def test_find_section(self):
        with XMLBuilder('REGTEXT') as ctx:
            ctx.AMDPAR("In 200.1 revise paragraph (b) as follows:")
            with ctx.SECTION():
                ctx.SECTNO("200.1")
                ctx.SUBJECT("Authority and Purpose.")
                ctx.P(" (b) This part is very important. ")
            ctx.AMDPAR("In 200.3 revise paragraph (b)(1) as follows:")
            with ctx.SECTION():
                ctx.SECTNO("200.3")
                ctx.SUBJECT("Definitions")
                ctx.P(" (b)(1) Define a term here. ")

        amdpar_xml = ctx.xml.xpath('//AMDPAR')[0]
        section = diff.find_section(amdpar_xml)
        self.assertEqual(section.tag, 'SECTION')

        sectno_xml = section.xpath('./SECTNO')[0]
        self.assertEqual(sectno_xml.text, '200.1')

    def test_new_subpart_added(self):
        amended_label = Amendment('POST', '200-Subpart:B')
        self.assertTrue(diff.new_subpart_added(amended_label))

        amended_label = Amendment('PUT', '200-Subpart:B')
        self.assertFalse(diff.new_subpart_added(amended_label))

        amended_label = Amendment('POST', '200-Subpart:B-a-3')
        self.assertFalse(diff.new_subpart_added(amended_label))

    def test_find_subpart(self):
        with XMLBuilder("REGTEXT", PART='105', TITLE='12') as ctx:
            ctx.AMDPAR("6. Add subpart B to read as follows:")
            with ctx.SUBPART():
                ctx.HD(u"Subpart B—Requirements", SOURCE="HED")
                with ctx.SECTION():
                    ctx.SECTNO("105.30")
                    ctx.SUBJECT("First In New Subpart")
                    ctx.P("For purposes of this subpart, the follow apply:")
                    ctx.P('(a) "Agent" means agent.')

        amdpar_xml = ctx.xml.xpath('//AMDPAR')[0]
        subpart = diff.find_subpart(amdpar_xml)
        self.assertTrue(subpart is not None)

        headings = [s for s in subpart if s.tag == 'HD']
        self.assertEqual(headings[0].text, u"Subpart B—Requirements")

    def test_fix_section_node(self):
        with XMLBuilder("REGTEXT") as ctx:
            ctx.P("paragraph 1")
            ctx.P("paragraph 2")
        paragraphs = [p for p in ctx.xml if p.tag == 'P']

        with XMLBuilder("REGTEXT") as ctx:
            with ctx.SECTION():
                ctx.SECTNO(" 205.4 ")
                ctx.SUBJECT("[Corrected]")
            ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                       u"follows:")
        par = ctx.xml.xpath('//AMDPAR')[0]
        section = diff.fix_section_node(paragraphs, par)
        self.assertNotEqual(None, section)
        section_paragraphs = [p for p in section if p.tag == 'P']
        self.assertEqual(2, len(section_paragraphs))

        self.assertEqual(section_paragraphs[0].text, 'paragraph 1')
        self.assertEqual(section_paragraphs[1].text, 'paragraph 2')

    def test_find_section_paragraphs(self):
        with XMLBuilder("REGTEXT") as ctx:
            with ctx.SECTION():
                ctx.SECTNO(" 205.4 ")
                ctx.SUBJECT("[Corrected]")
            ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                       u"follows:")
            ctx.P("(b) paragraph 1")

        amdpar = ctx.xml.xpath('//AMDPAR')[0]
        section = diff.find_section(amdpar)
        self.assertNotEqual(None, section)
        paragraphs = [p for p in section if p.tag == 'P']
        self.assertEqual(paragraphs[0].text, '(b) paragraph 1')

    def test_find_lost_section(self):
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT():
                ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                           u"follows:")
            with ctx.REGTEXT():
                with ctx.SECTION():
                    ctx.SECTNO(" 205.4 ")
                    ctx.SUBJECT("[Corrected]")
        amdpar = ctx.xml.xpath('//AMDPAR')[0]
        section = diff.find_lost_section(amdpar)
        self.assertNotEqual(None, section)

    def test_find_section_lost(self):
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT():
                ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                           u"follows:")
            with ctx.REGTEXT():
                with ctx.SECTION():
                    ctx.SECTNO(" 205.4 ")
                    ctx.SUBJECT("[Corrected]")
        amdpar = ctx.xml.xpath('//AMDPAR')[0]
        section = diff.find_section(amdpar)
        self.assertNotEqual(None, section)
