from datetime import date
import os
from time import time
from unittest import TestCase

import click
from click.testing import CliRunner
from mock import patch

from regparser import eregs_index
from regparser.commands import annual_editions
from regparser.history.versions import Version


class CommandsAnnualEditions(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_last_versions_raises_exception(self):
        """If there are no versions available, we should receive an
        exception"""
        with self.cli.isolated_filesystem():
            with self.assertRaises(click.UsageError):
                list(annual_editions.last_versions('12', '1000'))

    def test_last_versions_multiple_versions(self):
        """If multiple versions affect the same annual edition, we should only
        receive the last"""
        with self.cli.isolated_filesystem():
            path = eregs_index.VersionPath('12', '1000')
            path.write(Version('1111', date(2000, 12, 1), date(2000, 12, 1)))
            path.write(Version('2222', date(2000, 12, 2), date(2000, 12, 2)))
            path.write(Version('3333', date(2001, 12, 1), date(2001, 12, 1)))

            results = list(annual_editions.last_versions(12, 1000))
            self.assertEqual(results, [
                annual_editions.LastVersionInYear('2222', 2001),
                annual_editions.LastVersionInYear('3333', 2002)])

    def test_process_if_needed_missing_dependency_error(self):
        """If the annual XML or version isn't present, we should see a
        dependency error."""
        with self.cli.isolated_filesystem():
            last_versions = [annual_editions.LastVersionInYear('1111', 2000)]

            with self.assertRaises(eregs_index.DependencyException):
                annual_editions.process_if_needed('12', '1000', last_versions)

            eregs_index.VersionPath('12', '1000').write(
                Version('1111', date(2000, 1, 1), date(2000, 1, 1)))

            with self.assertRaises(eregs_index.DependencyException):
                annual_editions.process_if_needed('12', '1000', last_versions)

    @patch("regparser.commands.annual_editions.process")
    def test_process_if_needed_missing_writes(self, process):
        """If output isn't already present, we should process. If it is
        present, we don't need to, unless a dependency has changed."""
        with self.cli.isolated_filesystem():
            last_versions = [annual_editions.LastVersionInYear('1111', 2000)]
            eregs_index.VersionPath('12', '1000').write(
                Version('1111', date(2000, 1, 1), date(2000, 1, 1)))
            eregs_index.Path('annual', '12', '1000').write('2000', 'Annual')

            annual_editions.process_if_needed('12', '1000', last_versions)
            self.assertTrue(process.called)

            process.reset_mock()
            eregs_index.Path('tree', '12', '1000').write('1111', 'tree-here')
            annual_editions.process_if_needed('12', '1000', last_versions)
            self.assertFalse(process.called)

            # Simulate a change to an input file
            os.utime(
                os.path.join(eregs_index.ROOT, 'annual', '12', '1000', '2000'),
                (time() + 1000, time() + 1000))
            annual_editions.process_if_needed('12', '1000', last_versions)
            self.assertTrue(process.called)
