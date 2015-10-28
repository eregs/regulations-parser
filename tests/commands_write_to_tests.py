from datetime import date
import os
import tempfile
import shutil
from unittest import TestCase

from click.testing import CliRunner

from regparser import eregs_index
from regparser.commands.write_to import write_to
from regparser.history.versions import Version
from regparser.tree.struct import Node


class CommandsWriteToTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def add_versions(self):
        """Add some versions to the index"""
        eregs_index.VersionEntry('12', '1000', 'v1').write(
            Version('v1', date(2001, 1, 1), date(2001, 1, 1)))
        eregs_index.VersionEntry('12', '1000', 'v2').write(
            Version('v2', date(2002, 2, 2), date(2002, 2, 2)))
        eregs_index.VersionEntry('12', '1000', 'v3').write(
            Version('v3', date(2003, 3, 3), date(2003, 3, 3)))
        eregs_index.VersionEntry('12', '1001', 'other').write(
            Version('other', date(2003, 3, 3), date(2003, 3, 3)))

    def add_trees(self):
        """Add some versions to the index"""
        eregs_index.TreeEntry('12', '1000', 'v2').write(Node('v2'))
        eregs_index.TreeEntry('12', '1000', 'v3').write(Node('v3'))
        eregs_index.TreeEntry('12', '1000', 'v4').write(Node('v4'))

    def add_layers(self):
        """Add an assortment of layers to the index"""
        eregs_index.LayerEntry('12', '1000', 'v2', 'layer1').write({'1': 1})
        eregs_index.LayerEntry('12', '1000', 'v2', 'layer2').write({'2': 2})
        eregs_index.LayerEntry('12', '1000', 'v3', 'layer2').write({'2': 2})
        eregs_index.LayerEntry('12', '1000', 'v3', 'layer3').write({'3': 3})
        eregs_index.LayerEntry('12', '1000', 'v0', 'layer1').write({'1': 1})

    def add_diffs(self):
        """Adds an uneven assortment of diffs between trees"""
        eregs_index.DiffEntry('12', '1000', 'v1', 'v2').write({'1': 2})
        eregs_index.DiffEntry('12', '1000', 'v2', 'v2').write({'2': 2})
        eregs_index.DiffEntry('12', '1000', 'v2', 'v1').write({'2': 1})
        eregs_index.DiffEntry('12', '1000', 'v0', 'v1').write({'0': 1})

    def add_notices(self):
        """Adds an uneven assortment of notices"""
        eregs_index.SxSEntry('v0').write({'0': 0})
        eregs_index.SxSEntry('v1').write({'1': 1})
        eregs_index.SxSEntry('v2').write({'2': 2})

    def assert_file_exists(self, *parts):
        """Helper method to verify that a file was created"""
        path = os.path.join(self.tmpdir, *parts)
        self.assertTrue(os.path.exists(path))

    def test_integration(self):
        """Create a (small) set of files in the index. These files have
        various mismatches between version information -- we should only write
        the files which have an associated version"""
        with self.cli.isolated_filesystem():
            self.add_versions()
            self.add_trees()
            self.add_layers()
            self.add_diffs()
            self.add_notices()
            self.cli.invoke(write_to, ['12', '1000', self.tmpdir])

            self.assert_file_exists('regulation', '1000', 'v2')
            self.assert_file_exists('regulation', '1000', 'v3')
            # v4 is skipped as there is no corresponding version

            self.assert_file_exists('layer', 'layer1', '1000', 'v2')
            self.assert_file_exists('layer', 'layer2', '1000', 'v2')
            self.assert_file_exists('layer', 'layer2', '1000', 'v3')
            self.assert_file_exists('layer', 'layer3', '1000', 'v3')
            # v0, layer1 is skipped as there is no corresponding version

            self.assert_file_exists('diff', '1000', 'v1', 'v2')
            self.assert_file_exists('diff', '1000', 'v2', 'v2')
            self.assert_file_exists('diff', '1000', 'v2', 'v1')
            # v0, v1 is skipped as there is no corresponding version

            # v0 is skipped as there is no corresponding version
            self.assert_file_exists('notice', 'v1')
            self.assert_file_exists('notice', 'v2')
