from datetime import date
from unittest import TestCase

from click.testing import CliRunner
from mock import patch

from regparser.commands import layers
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.tree.struct import Node


class CommandsLayersTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_stale_cfr_layers(self):
        """We should have dependencies between all of the CFR layers and their
        associated trees. We should also tie the meta layer to the version"""
        configured_layers = {'cfr': {'keyterms': None, 'other': None}}
        with self.cli.isolated_filesystem(), patch.dict(
                layers.LAYER_CLASSES, configured_layers):
            version_entry = entry.Version(111, 22, 'aaa')
            version_entry.write(Version('aaa', date.today(), date.today()))
            # Use list() to instantiate
            self.assertRaises(dependency.Missing,
                              list, layers.stale_cfr_layers(version_entry))

            entry.Entry('tree', 111, 22, 'bbb').write('')    # wrong version
            self.assertRaises(dependency.Missing,
                              list, layers.stale_cfr_layers(version_entry))

            entry.Entry('tree', 111, 22, 'aaa').write('')
            self.assertItemsEqual(
                layers.stale_cfr_layers(version_entry),
                ['keyterms', 'other'])

            with dependency.Graph().dependency_db() as db:
                self.assertIn(
                    str(version_entry),
                    db[str(entry.Layer.cfr(111, 22, 'aaa', 'meta'))])

    def test_process_cfr_layers(self):
        """All layers for a single version should get written."""
        with self.cli.isolated_filesystem():
            version_entry = entry.Version(12, 1000, '1234')
            version_entry.write(Version('1234', date.today(), date.today()))
            entry.Tree('12', '1000', '1234').write(Node())

            layers.process_cfr_layers(
                ['keyterms', 'meta'], 12, version_entry)

            self.assertEqual(
                entry.Layer.cfr(12, 1000, '1234', 'keyterms').read(), {})
            self.assertEqual(
                entry.Layer.cfr(12, 1000, '1234', 'meta').read(), {})
