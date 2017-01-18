from unittest import TestCase

import pytest
from click.testing import CliRunner
from mock import patch

from regparser.commands.notice_preamble import notice_preamble
from regparser.index import dependency, entry


@pytest.mark.django_db
class CommandsNoticePreambleTests(TestCase):
    @patch('regparser.commands.notice_preamble.parse_preamble')
    def test_notice_preamble(self, parse_preamble):
        """A preprocessed notice must be present before we can parse the
        preamble. If we've already written a preamble, we don't need to
        process it again"""
        parse_preamble.return_value = {'example': 'preamble'}
        cli = CliRunner()
        with cli.isolated_filesystem():
            result = cli.invoke(notice_preamble, ['111-222'])
            self.assertIsInstance(result.exception, dependency.Missing)
            self.assertFalse(parse_preamble.called)

            entry.Entry('notice_xml', '111-222').write(b'<ROOT />')
            result = cli.invoke(notice_preamble, ['111-222'])
            self.assertIsNone(result.exception)
            self.assertTrue(parse_preamble.called)

            parse_preamble.reset_mock()
            result = cli.invoke(notice_preamble, ['111-222'])
            self.assertIsNone(result.exception)
            self.assertFalse(parse_preamble.called)
