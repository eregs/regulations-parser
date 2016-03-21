from contextlib import contextmanager
import os
import tempfile
import shutil
from unittest import TestCase

from click.testing import CliRunner

from regparser.commands.write_to import write_to
from regparser.index import entry
from regparser.tree.struct import Node


class CommandsWriteToTests(TestCase):
    def add_trees(self):
        """Add some versions to the index"""
        entry.Tree('12', '1000', 'v2').write(Node('v2'))
        entry.Tree('12', '1000', 'v3').write(Node('v3'))
        entry.Tree('12', '1000', 'v4').write(Node('v4'))
        entry.Tree('11', '1000', 'v5').write(Node('v5'))
        entry.Tree('12', '1001', 'v6').write(Node('v6'))

    def add_layers(self):
        """Add an assortment of layers to the index"""
        entry.Layer.cfr('12', '1000', 'v2', 'layer1').write({'1': 1})
        entry.Layer.cfr('12', '1000', 'v2', 'layer2').write({'2': 2})
        entry.Layer.cfr('12', '1000', 'v3', 'layer2').write({'2': 2})
        entry.Layer.cfr('12', '1000', 'v3', 'layer3').write({'3': 3})
        entry.Layer.cfr('11', '1000', 'v4', 'layer4').write({'4': 4})
        entry.Layer.cfr('12', '1001', 'v3', 'layer3').write({'3': 3})

    def add_diffs(self):
        """Adds an uneven assortment of diffs between trees"""
        entry.Diff('12', '1000', 'v1', 'v2').write({'1': 2})
        entry.Diff('12', '1000', 'v2', 'v2').write({'2': 2})
        entry.Diff('12', '1000', 'v2', 'v1').write({'2': 1})
        entry.Diff('12', '1000', 'v0', 'v1').write({'0': 1})
        entry.Diff('11', '1000', 'v3', 'v1').write({'3': 1})
        entry.Diff('12', '1001', 'v3', 'v1').write({'3': 1})

    def add_notices(self):
        """Adds an uneven assortment of notices"""
        data = {'doc_number': 'v0', 'cfr_title': 11, 'cfr_parts': []}
        entry.SxS('v0').write(data)
        data.update(cfr_parts=['1000'], doc_number='v1')
        entry.SxS('v1').write(data)
        data.update(cfr_title=12, doc_number='v2')
        entry.SxS('v2').write(data)
        data['doc_number'] = 'v3'
        entry.SxS('v3').write(data)

    def file_exists(self, *parts):
        """Helper method to verify that a file was created"""
        path = os.path.join(self.tmpdir, *parts)
        return os.path.exists(path)

    @contextmanager
    def integration(self):
        """Create a (small) set of files in the index. Handles setup and
        teardown of temporary directories"""
        cli = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        with cli.isolated_filesystem():
            self.add_trees()
            self.add_layers()
            self.add_diffs()
            self.add_notices()
            yield cli
        shutil.rmtree(self.tmpdir)

    def test_cfr_title_part(self):
        """Integration test that verifies only files associated with the
        requested CFR title/part are created"""
        with self.integration() as cli:
            cli.invoke(write_to, [self.tmpdir, '--cfr_title', '12',
                                  '--cfr_part', '1000'])

            self.assertTrue(self.file_exists('regulation', '1000', 'v2'))
            self.assertTrue(self.file_exists('regulation', '1000', 'v3'))
            self.assertTrue(self.file_exists('regulation', '1000', 'v4'))
            # these don't match the requested cfr title/part
            self.assertFalse(self.file_exists('regulation', '1000', 'v5'))
            self.assertFalse(self.file_exists('regulation', '1001', 'v6'))

            self.assertTrue(self.file_exists('layer', 'layer1', '1000', 'v2'))
            self.assertTrue(self.file_exists('layer', 'layer2', '1000', 'v2'))
            self.assertTrue(self.file_exists('layer', 'layer2', '1000', 'v3'))
            self.assertTrue(self.file_exists('layer', 'layer3', '1000', 'v3'))
            # these don't match the requested cfr title/part
            self.assertFalse(self.file_exists('layer', 'layer4', '1000', 'v4'))
            self.assertFalse(self.file_exists('layer', 'layer3', '1001', 'v3'))

            self.assertTrue(self.file_exists('diff', '1000', 'v1', 'v2'))
            self.assertTrue(self.file_exists('diff', '1000', 'v2', 'v2'))
            self.assertTrue(self.file_exists('diff', '1000', 'v2', 'v1'))
            # these don't match the requested cfr title/part
            self.assertFalse(self.file_exists('diff', '1000', 'v3', 'v1'))
            self.assertFalse(self.file_exists('diff', '1001', 'v3', 'v1'))

            self.assertTrue(self.file_exists('notice', 'v2'))
            self.assertTrue(self.file_exists('notice', 'v3'))
            # these don't match the requested cfr title/part
            self.assertFalse(self.file_exists('notice', 'v0'))
            self.assertFalse(self.file_exists('notice', 'v1'))

    def test_cfr_title(self):
        """Integration test that verifies only files associated with the
        requested CFR title are created"""
        with self.integration() as cli:
            cli.invoke(write_to, [self.tmpdir, '--cfr_title', '12'])

            self.assertFalse(self.file_exists('regulation', '1000', 'v5'))
            self.assertTrue(self.file_exists('regulation', '1001', 'v6'))
            self.assertFalse(self.file_exists('layer', 'layer4', '1000', 'v4'))
            self.assertTrue(self.file_exists('layer', 'layer3', '1001', 'v3'))
            self.assertFalse(self.file_exists('diff', '1000', 'v3', 'v1'))
            self.assertTrue(self.file_exists('diff', '1001', 'v3', 'v1'))
            self.assertFalse(self.file_exists('notice', 'v0'))
            self.assertFalse(self.file_exists('notice', 'v1'))

    def test_no_params(self):
        """Integration test that all local files are written"""
        with self.integration() as cli:
            cli.invoke(write_to, [self.tmpdir])

            self.assertTrue(self.file_exists('regulation', '1000', 'v5'))
            self.assertTrue(self.file_exists('layer', 'layer4', '1000', 'v4'))
            self.assertTrue(self.file_exists('diff', '1000', 'v3', 'v1'))
            self.assertTrue(self.file_exists('notice', 'v0'))
            self.assertTrue(self.file_exists('notice', 'v1'))
