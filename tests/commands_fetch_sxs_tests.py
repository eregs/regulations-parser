# @todo - right now this is a copy-paste from parse_rule_changes. SxS and
# rule changes will develop different data structures, however, so these files
# will diverge soon
from unittest import TestCase

from click.testing import CliRunner
from lxml import etree
from mock import patch

from regparser import eregs_index
from regparser.commands.fetch_sxs import fetch_sxs
from regparser.notice.xml import NoticeXML
from tests.xml_builder import XMLBuilderMixin


class CommandsFetchSxSTests(XMLBuilderMixin, TestCase):
    def setUp(self):
        super(CommandsFetchSxSTests, self).setUp()
        self.cli = CliRunner()
        with self.tree.builder("ROOT") as root:
            root.PRTPAGE(P="1234")
        self.notice_xml = NoticeXML(self.tree.render_xml())

    def test_missing_notice(self):
        """If the necessary notice XML is not present, we should expect a
        dependency error"""
        with self.cli.isolated_filesystem():
            result = self.cli.invoke(fetch_sxs, ['1111'])
            self.assertTrue(isinstance(result.exception,
                                       eregs_index.DependencyException))

    @patch('regparser.commands.fetch_sxs.process_xml')
    def test_writes(self, process_xml):
        """If the notice XML is present, we write the parsed version to disk,
        even if that version's already present"""
        with self.cli.isolated_filesystem():
            eregs_index.NoticeEntry('1111').write(self.notice_xml)
            self.cli.invoke(fetch_sxs, ['1111'])
            self.assertTrue(process_xml.called)
            args = process_xml.call_args[0]
            self.assertTrue(isinstance(args[0], dict))
            self.assertTrue(isinstance(args[1], etree._Element))

            process_xml.reset_mock()
            eregs_index.Entry('rule_changes', '1111').write('content')
            self.cli.invoke(fetch_sxs, ['1111'])
            self.assertTrue(process_xml.called)
