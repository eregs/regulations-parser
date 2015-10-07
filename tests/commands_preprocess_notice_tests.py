from unittest import TestCase

from click.testing import CliRunner
from mock import patch

from regparser import eregs_index
from regparser.commands.preprocess_notice import preprocess_notice
from regparser.notice.dates import fetch_effective_date
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
        return self.tree.render_xml()

    @patch('regparser.commands.preprocess_notice.xmls_for_url')
    def test_single_notice(self, xmls_for_url):
        """Integration test, verifying that if a document number is associated
        with only a single XML file, a single, modified result is written"""
        cli = CliRunner()
        self.expect_json_http({'full_text_xml_url': 'some://url',
                               'effective_on': '2008-08-08'})
        xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(eregs_index.Path("notice_xml")))

            written = eregs_index.Path("notice_xml").read_xml("1234-5678")
            self.assertEqual(fetch_effective_date(written), '2008-08-08')

    @patch('regparser.commands.preprocess_notice.xmls_for_url')
    def test_split_notice(self, xmls_for_url):
        """Integration test, testing whether a notice which has been split
        (due to having multiple effective dates) is written as multiple
        files"""
        cli = CliRunner()
        self.expect_json_http({'full_text_xml_url': 'some://url',
                               'effective_on': '2008-08-08'})
        xmls_for_url.return_value = [
            self.example_xml("Effective January 1, 2001"),
            self.example_xml("Effective February 2, 2002"),
            self.example_xml("Effective March 3, 2003")]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            path = eregs_index.Path("notice_xml")
            self.assertEqual(3, len(path))

            jan_xml = path.read_xml("1234-5678_20010101")
            feb_xml = path.read_xml("1234-5678_20020202")
            mar_xml = path.read_xml("1234-5678_20030303")

            self.assertEqual(fetch_effective_date(jan_xml), '2001-01-01')
            self.assertEqual(fetch_effective_date(feb_xml), '2002-02-02')
            self.assertEqual(fetch_effective_date(mar_xml), '2003-03-03')
