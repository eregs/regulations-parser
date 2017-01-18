from datetime import date
from unittest import TestCase

import pytest
import six
from click.testing import CliRunner
from mock import patch

from regparser.commands import layers
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.tree.struct import Node


@pytest.mark.django_db
class CommandsLayersTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_stale_layers(self):
        """We should have dependencies between all of the layers and their
        associated trees. We should also tie the meta layer to the version"""
        configured_layers = {'cfr': {'keyterms': None, 'other': None}}
        with self.cli.isolated_filesystem(), patch.dict(
                layers.LAYER_CLASSES, configured_layers):
            version_entry = entry.Version(111, 22, 'aaa')
            version_entry.write(Version('aaa', date.today(), date.today()))
            tree_entry = entry.Tree(111, 22, 'aaa')
            self.assertRaises(dependency.Missing, layers.stale_layers,
                              tree_entry, 'cfr')

            entry.Entry('tree', 111, 22, 'bbb').write(b'')    # wrong version
            self.assertRaises(dependency.Missing, layers.stale_layers,
                              tree_entry, 'cfr')

            entry.Entry('tree', 111, 22, 'aaa').write(b'')
            six.assertCountEqual(
                self,
                layers.stale_layers(tree_entry, 'cfr'), ['keyterms', 'other'])

            self.assertIn(
                str(version_entry),
                dependency.Graph().dependencies(
                    str(entry.Layer.cfr(111, 22, 'aaa', 'meta'))))

    def test_process_cfr_layers(self):
        """All layers for a single version should get written."""
        with self.cli.isolated_filesystem():
            version_entry = entry.Version(12, 1000, '1234')
            version_entry.write(Version('1234', date.today(), date.today()))
            entry.Tree('12', '1000', '1234').write(Node())

            layers.process_cfr_layers(
                ['keyterms', 'meta'], 12, version_entry)

            self.assertTrue(
                entry.Layer.cfr(12, 1000, '1234', 'keyterms').exists())
            self.assertTrue(
                entry.Layer.cfr(12, 1000, '1234', 'meta').exists())

    def test_process_preamble_layers(self):
        """All layers for a single preamble should get written."""
        with self.cli.isolated_filesystem():
            preamble_entry = entry.Preamble('111_222')
            preamble_entry.write(Node())

            layers.process_preamble_layers(['graphics'], preamble_entry)

            self.assertTrue(
                entry.Layer.preamble('111_222', 'graphics').exists())
