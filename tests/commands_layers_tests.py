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

    @patch('regparser.commands.layers.sxs_source_names')
    def test_dependencies(self, sxs_source_names):
        """We should have dependencies between all of the layers and their
        associated trees. We should also have a tie from the meta layer to the
        version info, and between the SxS layer and all of the preceding sxs
        inputs"""
        with self.cli.isolated_filesystem():
            tree_dir = entry.Entry('tree')
            layer_dir = entry.Entry('layer')
            version_dir = entry.Entry('version')
            sxs_dir = entry.Entry('sxs')

            # Trees
            (tree_dir / '1111').write('tree1')
            (tree_dir / '2222').write('tree2')
            (tree_dir / '3333').write('tree3')
            sxs_source_names.return_value = ['1111']

            deps = layers.dependencies(tree_dir, layer_dir, version_dir)
            simple_layers = [
                'external-citations', 'internal-citations', 'toc',
                'interpretations', 'terms', 'paragraph-markers', 'keyterms',
                'formatting', 'graphics']

            with deps.dependency_db() as db:
                graph = dict(db)    # copy
            for version_id in ('1111', '2222', '3333'):
                for layer_name in simple_layers:
                    self.assertEqual(
                        graph[str(layer_dir / version_id / layer_name)],
                        set([str(tree_dir / version_id)]))
                self.assertEqual(
                    graph[str(layer_dir / version_id / 'meta')],
                    set([str(tree_dir / version_id),
                         str(version_dir / version_id)]))
            self.assertEqual(
                graph[str(layer_dir / '1111' / 'analyses')],
                set([str(tree_dir / '1111'), str(sxs_dir / '1111')]))
            self.assertEqual(
                graph[str(layer_dir / '2222' / 'analyses')],
                set([str(tree_dir / '2222'), str(sxs_dir / '1111')]))
            self.assertEqual(
                graph[str(layer_dir / '3333' / 'analyses')],
                set([str(tree_dir / '3333'), str(sxs_dir / '1111')]))

    def test_sxs_sources(self):
        """We should read back serialized notices, but only those which are
        relevant"""
        with self.cli.isolated_filesystem():
            notice_dir = entry.Entry('notice_xml')
            version_dir = entry.Entry('version')
            sxs_dir = entry.SxS()
            # 4 won't be picked up as there's no associated version
            for i in (1, 3, 4):
                (notice_dir / i).write(str(i))
                (sxs_dir / i).write({str(i): i})

            for i in range(1, 4):
                (version_dir / i).write(str(i))

            self.assertEqual([{'1': 1}], layers.sxs_sources(version_dir, '1'))
            self.assertEqual([{'1': 1}], layers.sxs_sources(version_dir, '2'))
            self.assertEqual([{'1': 1}, {'3': 3}],
                             layers.sxs_sources(version_dir, '3'))

    @patch('regparser.commands.layers.sxs_sources')
    def test_process_layers(self, sxs_sources):
        """All layers for a single version should get written."""
        with self.cli.isolated_filesystem():
            meta, analyses = Mock(), Mock()
            sxs_sources.return_value = "Fake Notices"
            meta.return_value.build.return_value = {'1': 1}
            analyses.return_value.build.return_value = {'2': 2}

            version = Version('1234', date(2000, 1, 1), date(2000, 1, 1))
            entry.Tree('12', '1000', '1234').write(Node())

            with patch.dict(layers.LAYER_CLASSES,
                            {'cfr': {'meta': meta, 'analyses': analyses}}):
                layers.process_layers(
                    ['meta', 'analyses'], '12', '1000', version)
            self.assertEqual(meta.call_args[1].get('notices'), [])
            self.assertEqual(analyses.call_args[1].get('notices'),
                             "Fake Notices")
