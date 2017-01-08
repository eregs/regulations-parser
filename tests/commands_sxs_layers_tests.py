from datetime import date
from unittest import TestCase

import pytest
from click.testing import CliRunner

from regparser.commands import sxs_layers
from regparser.history.versions import Version
from regparser.index import dependency, entry


@pytest.mark.django_db
class CommandsSxSLayersTests(TestCase):
    def create_versions(self):
        entry.Version(11, 222, 'aaa').write(
            Version('aaa', date(2002, 2, 2), date(2002, 2, 2)))
        entry.Version(11, 222, 'bbb').write(
            Version('bbb', date(2001, 1, 1), date(2001, 1, 1)))
        entry.Version(11, 222, 'ccc').write(
            Version('ccc', date(2003, 3, 3), date(2003, 3, 3)))

    def test_previous_sxs(self):
        """Should return SxS in version order; should only include SxS until
        the stop_version specified"""
        with CliRunner().isolated_filesystem():
            self.create_versions()
            self.assertEqual(
                [s.path[0] for s in sxs_layers.previous_sxs(11, 222, 'aaa')],
                ['bbb', 'aaa'])
            self.assertEqual(
                [s.path[0] for s in sxs_layers.previous_sxs(11, 222, 'bbb')],
                ['bbb'])
            self.assertEqual(
                [s.path[0] for s in sxs_layers.previous_sxs(11, 222, 'ccc')],
                ['bbb', 'aaa', 'ccc'])

    def test_is_stale(self):
        """We should raise dependency exceptions when necessary files haven't
        been processed. We need SxS entries _and_ the relevant tree"""
        with CliRunner().isolated_filesystem():
            self.assertRaises(dependency.Missing, sxs_layers.is_stale,
                              11, 222, 'aaa')

            self.create_versions()
            entry.Entry('sxs', 'aaa').write(b'')
            entry.Entry('sxs', 'bbb').write(b'')
            self.assertRaises(dependency.Missing, sxs_layers.is_stale,
                              11, 222, 'aaa')

            entry.Entry('tree', 11, 222, 'bbb').write(b'')   # Wrong tree
            self.assertRaises(dependency.Missing, sxs_layers.is_stale,
                              11, 222, 'aaa')

            entry.Entry('tree', 11, 222, 'aaa').write(b'')
            self.assertTrue(sxs_layers.is_stale(11, 222, 'aaa'))
