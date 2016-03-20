from datetime import date
from unittest import TestCase

from click.testing import CliRunner
from mock import Mock, patch

from regparser.commands import layers
from regparser.history.versions import Version
from regparser.index import entry
from regparser.tree.struct import Node


class CommandsLayersTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_dependencies(self):
        """We should have dependencies between all of the layers and their
        associated trees. We should also have a tie from the meta layer to the
        version info"""
        with self.cli.isolated_filesystem():
            tree_dir = entry.Entry('tree')
            layer_dir = entry.Entry('layer')
            version_dir = entry.Entry('version')

            # Trees
            (tree_dir / '1111').write('tree1')
            (tree_dir / '2222').write('tree2')
            (tree_dir / '3333').write('tree3')

            deps = layers.dependencies(tree_dir, layer_dir, version_dir)
            layer_names = [
                'external-citations', 'internal-citations', 'toc',
                'interpretations', 'terms', 'paragraph-markers', 'keyterms',
                'formatting', 'graphics']

            with deps.dependency_db() as db:
                graph = dict(db)    # copy
            for version_id in ('1111', '2222', '3333'):
                for layer_name in layer_names:
                    self.assertEqual(
                        graph[str(layer_dir / version_id / layer_name)],
                        set([str(tree_dir / version_id)]))
                self.assertEqual(
                    graph[str(layer_dir / version_id / 'meta')],
                    set([str(tree_dir / version_id),
                         str(version_dir / version_id)]))

    def test_process_layers(self):
        """All layers for a single version should get written."""
        with self.cli.isolated_filesystem():
            meta, keyterms = Mock(), Mock()
            meta.return_value.build.return_value = {'1': 1}
            keyterms.return_value.build.return_value = {'2': 2}

            version = Version('1234', date(2000, 1, 1), date(2000, 1, 1))
            entry.Tree('12', '1000', '1234').write(Node())

            with patch.dict(layers.LAYER_CLASSES,
                            {'cfr': {'meta': meta, 'keyterms': keyterms}}):
                layers.process_layers(
                    ['meta', 'keyterms'], '12', '1000', version)
            self.assertTrue(meta.called)
            self.assertTrue(keyterms.called)
