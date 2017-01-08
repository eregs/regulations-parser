import re
from datetime import date
from unittest import TestCase

import pytest
from click.testing import CliRunner
from lxml import etree
from mock import patch

from regparser.commands.preprocess_notice import (convert_cfr_refs,
                                                  preprocess_notice)
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML, TitlePartsRef
from regparser.test_utils.http_mixin import HttpMixin
from regparser.test_utils.xml_builder import XMLBuilder


@pytest.mark.django_db
class CommandsPreprocessNoticeTests(HttpMixin, TestCase):
    def example_xml(self, effdate_str="", source=None):
        """Returns a simple notice-like XML structure"""
        with XMLBuilder("ROOT") as ctx:
            ctx.CONTENT()
            ctx.P()
            with ctx.EFFDATE():
                ctx.P(effdate_str)
        return NoticeXML(ctx.xml, source)

    def expect_common_json(self, **kwargs):
        """Expect an HTTP call and return a common json respond"""
        params = {'effective_on': '2008-08-08',
                  'publication_date': '2007-07-07',
                  'full_text_xml_url': 'some://url',
                  'volume': 45,
                  'start_page': 111,
                  'end_page': 222}
        params.update(kwargs)
        self.expect_json_http(params, uri=re.compile('.*federalregister.*'))
        # No data from regs.gov
        self.expect_json_http({}, uri=re.compile('.*regulations.*'))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice(self, notice_xmls_for_url):
        """Integration test, verifying that if a document number is associated
        with only a single XML file, a single, modified result is written"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.effective, date(2008, 8, 8))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_comments_close_on_meta(self, notice_xmls_for_url):
        """
        Verify that when we have metadata for the comment closing date, we
        write it to the object.
        """
        cli = CliRunner()
        self.expect_common_json(comments_close_on="2010-10-10")
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.comments_close_on, date(2010, 10, 10))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_comments_close_on_xml(self, notice_xmls_for_url):
        """
        Verify that when we have XML info but no metadata for the comment
        closing date, we still write it to the object.
        """
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml(
            "Comments close on November 11, 2011")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.comments_close_on, date(2011, 11, 11))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_comments_close_on_prefer(self, notice_xmls_for_url):
        """
        Verify that when we XML and metadata for the comment
        closing date, we use the metadata.
        """
        cli = CliRunner()
        self.expect_common_json(comments_close_on="2010-10-10")
        notice_xmls_for_url.return_value = [self.example_xml(
            "Comments close on November 11, 2011")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.comments_close_on, date(2010, 10, 10))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_one_agency_meta(self, notice_xmls_for_url):
        """
        Verify that we get agency info from the metadata.
        """
        cli = CliRunner()
        agencies_info = [{
            u'name': u'Environmental Protection Agency',
            u'parent_id': None,
            u'raw_name': u'ENVIRONMENTAL PROTECTION AGENCY',
            u'url': ('https://www.federalregister.gov/agencies/'
                     'environmental-protection-agency'),
            u'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                          '145.json'),
            u'id': 145
        }]
        self.expect_common_json(agencies=agencies_info)
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(len(written.xpath("//EREGS_AGENCIES")), 1)
            self.assertEqual(len(written.xpath("//EREGS_AGENCY")), 1)
            epa = written.xpath("//EREGS_AGENCY")[0]
            self.assertEqual(epa.attrib["name"],
                             "Environmental Protection Agency")
            self.assertEqual(epa.attrib["raw-name"],
                             "ENVIRONMENTAL PROTECTION AGENCY")
            self.assertEqual(epa.attrib["agency-id"],
                             "145")

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_rins(self, notice_xmls_for_url):
        """
        Verify that we get rins from the metadata and XMl.
        """
        cli = CliRunner()
        self.expect_common_json(regulation_id_numbers=["2050-AG65"])
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(len(written.xpath("//EREGS_RINS")), 1)
            self.assertEqual(len(written.xpath("//EREGS_RIN")), 1)
            rin = written.xpath("//EREGS_RIN")[0]
            self.assertEqual(rin.attrib["rin"], "2050-AG65")

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_docket_ids(self, notice_xmls_for_url):
        """
        Verify that we get docket_ids from the metadata.
        """
        cli = CliRunner()
        self.expect_common_json(docket_ids=["EPA-HQ-SFUND-2010-1086",
                                            "FRL-9925-69-OLEM"])
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(len(written.xpath("//EREGS_DOCKET_IDS")), 1)
            self.assertEqual(len(written.xpath("//EREGS_DOCKET_ID")), 2)
            did = written.xpath("//EREGS_DOCKET_ID")[0]
            self.assertEqual(did.attrib["docket_id"], "EPA-HQ-SFUND-2010-1086")
            did = written.xpath("//EREGS_DOCKET_ID")[1]
            self.assertEqual(did.attrib["docket_id"], "FRL-9925-69-OLEM")

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_missing_effective_date(self, notice_xmls_for_url):
        """We should not explode if no effective date is present. Instead, we
        should parse the effective date from the XML"""
        cli = CliRunner()
        self.expect_common_json(effective_on=None)
        notice_xmls_for_url.return_value = [
            self.example_xml("Effective January 1, 2001")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            written = entry.Notice('1234-5678').read()
            self.assertEqual(written.effective, date(2001, 1, 1))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_split_notice(self, notice_xmls_for_url):
        """Integration test, testing whether a notice which has been split
        (due to having multiple effective dates) is written as multiple
        files"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [
            self.example_xml("Effective January 1, 2001"),
            self.example_xml("Effective February 2, 2002"),
            self.example_xml("Effective March 3, 2003")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            notice_path = entry.Notice()
            self.assertEqual(3, len(list(entry.Notice().sub_entries())))

            jan = (notice_path / '1234-5678_20010101').read()
            feb = (notice_path / '1234-5678_20020202').read()
            mar = (notice_path / '1234-5678_20030303').read()

            self.assertEqual(jan.effective, date(2001, 1, 1))
            self.assertEqual(feb.effective, date(2002, 2, 2))
            self.assertEqual(mar.effective, date(2003, 3, 3))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_dependencies_local(self, notice_xmls_for_url):
        """If the xml comes from a local source, we should expect a dependency
        be present"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml(source='./here')]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            entry_str = str(entry.Notice() / '1234-5678')
            self.assertIn(entry_str, dependency.Graph())

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_dependencies_remote(self, notice_xmls_for_url):
        """If the xml comes from a remote source, we should not see a
        dependency"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml(source='./here')]
        notice_xmls_for_url.return_value[0].source = 'http://example.com'
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            entry_str = str(entry.Notice() / '1234-5678')
            assert len(dependency.Graph().dependencies(entry_str)) == 0

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_cfr_refs_from_metadata(self, notice_xmls_for_url):
        """
        Verify that we get CFR references from the metadata.
        """
        cli = CliRunner()
        self.expect_common_json(cfr_references=[
            {"title": "40", "part": "300"}, {"title": "40", "part": "301"}])
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(len(written.xpath("//EREGS_CFR_REFS")), 1)
            self.assertEqual(len(written.xpath("//EREGS_CFR_TITLE_REF")), 1)
            title = written.xpath("//EREGS_CFR_TITLE_REF")[0]
            self.assertEqual(title.attrib["title"], "40")
            self.assertEqual(len(written.xpath("//EREGS_CFR_PART_REF")), 2)
            part = written.xpath("//EREGS_CFR_PART_REF")[0]
            self.assertEqual(part.attrib["part"], "300")
            part = written.xpath("//EREGS_CFR_PART_REF")[1]
            self.assertEqual(part.attrib["part"], "301")

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice_cfr_refs_from_xml(self, notice_xmls_for_url):
        """
        Verify that we get CFR references from the xml.
        """
        cli = CliRunner()
        self.expect_common_json()
        notice_xml = self.example_xml()
        cfr_el = etree.SubElement(notice_xml.xml, 'CFR')
        cfr_el.text = '40 CFR 300, 301'
        notice_xmls_for_url.return_value = [notice_xml]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(list(entry.Notice().sub_entries())))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(len(written.xpath("//EREGS_CFR_REFS")), 1)
            self.assertEqual(len(written.xpath("//EREGS_CFR_TITLE_REF")), 1)
            title = written.xpath("//EREGS_CFR_TITLE_REF")[0]
            self.assertEqual(title.attrib["title"], "40")
            self.assertEqual(len(written.xpath("//EREGS_CFR_PART_REF")), 2)
            part = written.xpath("//EREGS_CFR_PART_REF")[0]
            self.assertEqual(part.attrib["part"], "300")
            part = written.xpath("//EREGS_CFR_PART_REF")[1]
            self.assertEqual(part.attrib["part"], "301")

    def test_convert_cfr_refs(self):
        """
        Test that we get the correct CFR references from the metadata
        """
        refs = [
            {"title": 40, "part": 300},
            {"title": 41, "part": 210},
            {"title": 40, "part": 301},
            {"title": 40, "part": 302},
            {"title": 40, "part": 303},
            {"title": 42, "part": 302},
            {"title": 42, "part": 303}
        ]
        expected = [
            TitlePartsRef(title=40, parts=[300, 301, 302, 303]),
            TitlePartsRef(title=41, parts=[210]),
            TitlePartsRef(title=42, parts=[302, 303])
        ]
        self.assertEqual(convert_cfr_refs(refs), expected)

        refs = [
            {"title": 42, "part": 302},
            {"title": 42, "part": 303},
            {"title": 40, "part": 330},
            {"title": 41, "part": 210},
            {"title": 40, "part": 300},
        ]
        expected = [
            TitlePartsRef(title=40, parts=[300, 330]),
            TitlePartsRef(title=41, parts=[210]),
            TitlePartsRef(title=42, parts=[302, 303])
        ]
        self.assertEqual(convert_cfr_refs(refs), expected)
