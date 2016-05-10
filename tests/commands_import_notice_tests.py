from unittest import TestCase

from regparser.commands import import_notice
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder


class CommandsImportNoticeTests(TestCase):
    def test_has_requirments(self):
        """Validate that certain attributes are required"""
        with XMLBuilder("ROOT", **{"eregs-version-id": "vvv"}) as ctx:
            ctx.PRTPAGE(P=44, **{"eregs-fr-volume": "124"})
            ctx.DATES(**{"eregs-published-date": "2005-05-05"})
        notice_xml = NoticeXML(ctx.xml_copy())
        self.assertTrue(import_notice.has_requirements(notice_xml))

        notice_xml = NoticeXML(ctx.xml_copy())
        del notice_xml.xml.attrib['eregs-version-id']
        self.assertFalse(import_notice.has_requirements(notice_xml))

        notice_xml = NoticeXML(ctx.xml_copy())
        del notice_xml.xml.xpath('//PRTPAGE')[0].attrib['eregs-fr-volume']
        self.assertFalse(import_notice.has_requirements(notice_xml))

        notice_xml = NoticeXML(ctx.xml_copy())
        del notice_xml.xml.xpath('//DATES')[0].attrib['eregs-published-date']
        self.assertFalse(import_notice.has_requirements(notice_xml))
