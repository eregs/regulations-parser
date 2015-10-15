from unittest import TestCase

from click.testing import CliRunner
from lxml import etree
from mock import patch

from regparser import eregs_index
from regparser.commands.parse_rule_changes import parse_rule_changes
from tests.xml_builder import XMLBuilderMixin


class CommandsParseRuleChangesTests(XMLBuilderMixin, TestCase):
    def setUp(self):
        super(CommandsParseRuleChangesTests, self).setUp()
        self.cli = CliRunner()
        with self.tree.builder("ROOT") as root:
            root.PRTPAGE(P="1234")
        self.xml_str = self.tree.render_string()

    def test_missing_notice(self):
        """If the necessary notice XML is not present, we should expect a
        dependency error"""
        with self.cli.isolated_filesystem():
            result = self.cli.invoke(parse_rule_changes, ['1111'])
            self.assertTrue(isinstance(result.exception,
                                       eregs_index.DependencyException))

    @patch('regparser.commands.parse_rule_changes.process_xml')
    def test_writes(self, process_xml):
        """If the notice XML is present, we write the parsed version to disk,
        even if that version's already present"""
        with self.cli.isolated_filesystem():
            eregs_index.Path('notice_xml').write('1111', self.xml_str)
            self.cli.invoke(parse_rule_changes, ['1111'])
            self.assertTrue(process_xml.called)
            args = process_xml.call_args[0]
            self.assertTrue(isinstance(args[0], dict))
            self.assertTrue(isinstance(args[1], etree._Element))

            process_xml.reset_mock()
            eregs_index.Path('rule_changes').write('1111', 'content')
            self.cli.invoke(parse_rule_changes, ['1111'])
            self.assertTrue(process_xml.called)
