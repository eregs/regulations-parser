from datetime import date
from unittest import TestCase

from click.testing import CliRunner
from mock import patch

from regparser import eregs_index
from regparser.commands.preprocess_notice import preprocess_notice
from regparser.notice.xml import NoticeXML
from tests.http_mixin import HttpMixin
from tests.xml_builder import LXMLBuilder, XMLBuilderMixin


class CommandsPreprocessNoticeTests(HttpMixin, XMLBuilderMixin, TestCase):
    def example_xml(self, effdate_str=""):
        """Returns a simple notice-like XML structure"""
        self.tree = LXMLBuilder()
        with self.tree.builder("ROOT") as root:
            root.CONTENT()
            root.P()
            with root.EFFDATE() as effdate:
                effdate.P(effdate_str)
        return NoticeXML(self.tree.render_xml())

    def expect_common_json(self):
        """Expect an HTTP call and return a common json respond"""
        self.expect_json_http({'effective_on': '2008-08-08',
                               'full_text_xml_url': 'some://url',
                               'publication_date': '2007-07-07',
                               'volume': 45})

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice(self, notice_xmls_for_url):
        """Integration test, verifying that if a document number is associated
        with only a single XML file, a single, modified result is written"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(eregs_index.NoticeEntry()))

            written = eregs_index.NoticeEntry('1234-5678').read()
            self.assertEqual(written.effective, date(2008, 8, 8))

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
            notice_path = eregs_index.NoticeEntry()
            self.assertEqual(3, len(notice_path))

            jan = (notice_path / '1234-5678_20010101').read()
            feb = (notice_path / '1234-5678_20020202').read()
            mar = (notice_path / '1234-5678_20030303').read()

            self.assertEqual(jan.effective, date(2001, 1, 1))
            self.assertEqual(feb.effective, date(2002, 2, 2))
            self.assertEqual(mar.effective, date(2003, 3, 3))
