from datetime import date
from unittest import TestCase

from click.testing import CliRunner
from mock import patch

from regparser.commands.preprocess_notice import preprocess_notice
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder
from tests.http_mixin import HttpMixin


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
                  'volume': 45}
        params.update(kwargs)
        self.expect_json_http(params)

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_single_notice(self, notice_xmls_for_url):
        """Integration test, verifying that if a document number is associated
        with only a single XML file, a single, modified result is written"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(entry.Notice()))

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
            self.assertEqual(1, len(entry.Notice()))

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
            self.assertEqual(1, len(entry.Notice()))

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
            self.assertEqual(1, len(entry.Notice()))

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
            u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                               u'agencies/environmental-protection-agency'),
            u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                    u'api/v1/agencies/145.json'),
            u'id': 145
        }]
        self.expect_common_json(agencies=agencies_info)
        notice_xmls_for_url.return_value = [self.example_xml()]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            self.assertEqual(1, len(entry.Notice()))

            written = entry.Notice('1234-5678').read()
            self.assertEqual(len(written.xpath("//EREGS_AGENCIES")), 1)
            self.assertEqual(len(written.xpath("//EREGS_AGENCY")), 1)
            epa = written.xpath("//EREGS_AGENCY")[0]
            self.assertEqual(epa.attrib["eregs-agency-name"],
                             "Environmental Protection Agency")
            self.assertEqual(epa.attrib["eregs-agency-raw-name"],
                             "ENVIRONMENTAL PROTECTION AGENCY")
            self.assertEqual(epa.attrib["eregs-agency-id"],
                             "145")

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
            self.assertEqual(3, len(notice_path))

            jan = (notice_path / '1234-5678_20010101').read()
            feb = (notice_path / '1234-5678_20020202').read()
            mar = (notice_path / '1234-5678_20030303').read()

            self.assertEqual(jan.effective, date(2001, 1, 1))
            self.assertEqual(feb.effective, date(2002, 2, 2))
            self.assertEqual(mar.effective, date(2003, 3, 3))

    @patch('regparser.commands.preprocess_notice.notice_xmls_for_url')
    def test_dependencies(self, notice_xmls_for_url):
        """If the xml comes from a local source, we should expect a dependency
        be present. Otherwise, we should expect no dependency"""
        cli = CliRunner()
        self.expect_common_json()
        notice_xmls_for_url.return_value = [self.example_xml(source='./here')]
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            entry_str = str(entry.Notice() / '1234-5678')
            self.assertIn(entry_str, dependency.Graph())

        notice_xmls_for_url.return_value[0].source = 'http://example.com'
        with cli.isolated_filesystem():
            cli.invoke(preprocess_notice, ['1234-5678'])
            entry_str = str(entry.Notice() / '1234-5678')
            self.assertNotIn(entry_str, dependency.Graph())
