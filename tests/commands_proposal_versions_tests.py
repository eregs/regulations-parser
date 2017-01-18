from datetime import date
from unittest import TestCase

import pytest
from click.testing import CliRunner
from mock import patch

from regparser.commands.proposal_versions import proposal_versions
from regparser.history.versions import Version
from regparser.index import dependency, entry


@pytest.mark.django_db
class CommandsProposalVersionsTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_missing_notice(self):
        """We should get an exception if the notice isn't present"""
        with self.cli.isolated_filesystem():
            result = self.cli.invoke(proposal_versions, ['1111'])
            self.assertTrue(isinstance(result.exception, dependency.Missing))
            self.assertEqual(result.exception.dependency,
                             str(entry.Notice('1111')))

    @patch('regparser.commands.proposal_versions.entry')
    def test_creates_version(self, entry):
        notice = entry.Notice.return_value.read.return_value
        notice.published = date.today()
        notice.cfr_ref_pairs = [(11, 111), (11, 222), (22, 222), (22, 333)]
        with self.cli.isolated_filesystem():
            result = self.cli.invoke(proposal_versions, ['dddd'])
            self.assertIsNone(result.exception)
            self.assertEqual('dddd', entry.Notice.call_args[0][0])
            self.assertEqual([lst[0] for lst in entry.Version.call_args_list],
                             [(11, 111, 'dddd'), (11, 222, 'dddd'),
                              (22, 222, 'dddd'), (22, 333, 'dddd')])
            self.assertEqual(entry.Version.return_value.write.call_args[0][0],
                             Version('dddd', date.today(), None))
