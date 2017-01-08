from contextlib import contextmanager
from datetime import timedelta
from unittest import TestCase

import pytest
import six
from click.testing import CliRunner
from django.utils import timezone

from regparser.index import dependency, entry
from regparser.web.index.models import Entry as DBEntry


@pytest.mark.django_db
class DependencyGraphTests(TestCase):
    @contextmanager
    def dependency_graph(self):
        with CliRunner().isolated_filesystem():
            path = entry.Entry('path')
            self.depender = path / 'depender'
            self.dependency = path / 'dependency'
            yield dependency.Graph()

    def _touch(self, filename, offset):
        """Update the modification time for a dependency"""
        time = timezone.now() + timedelta(hours=1)
        DBEntry.objects.filter(label_id=str(filename)).update(modified=time)

    def test_nonexistent_files_are_stale(self):
        """By definition, if a file is not present, it needs to be rebuilt"""
        with self.dependency_graph() as dgraph:
            self.dependency.write(b'value')
            dgraph.add(self.depender, self.dependency)
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))
            # shouldn't raise an exception; all dependencies are up to date
            dgraph.validate_for(self.depender)

    def test_nonexistant_deps_are_stale(self):
        """If a dependency is not present, we're stale"""
        with self.dependency_graph() as dgraph:
            self.depender.write(b'value')
            dgraph.add(self.depender, self.dependency)
            self.assertTrue(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))
            with self.assertRaises(dependency.Missing):
                dgraph.validate_for(self.depender)

    def test_updates_to_dependencies_flow(self):
        """If a dependency is updated, the graph should be recalculated"""
        with self.dependency_graph() as dgraph:
            self.dependency.write(b'value')
            self.depender.write(b'value2')
            dgraph.add(self.depender, self.dependency)
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertFalse(dgraph.is_stale(self.depender))

            self._touch(self.dependency, 1000)
            dgraph.rebuild()
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))

    def test_dependencies_serialized(self):
        """Every instance of dependency.Graph shares a serialized copy of the
        dependencies"""
        with self.dependency_graph() as dgraph:
            dgraph.add(self.depender, self.dependency / '1')
            dgraph.add(self.depender, self.dependency / '2')
            six.assertCountEqual(
                self,
                dgraph.dependencies(str(self.depender)),
                [str(self.dependency / 1), str(self.dependency / 2)])

            six.assertCountEqual(
                self,
                dependency.Graph().dependencies(str(self.depender)),
                [str(self.dependency / 1), str(self.dependency / 2)])

    def assert_rebuilt_state(self, graph, path, **kwargs):
        """Shorthand to verify that stale values are set appropriately.
        For example, self.assert_rebuilt_state(graph, path, a='a', b='ab')
        verifies that path/a is stale due to path/a and path/b is stale due to
        either path/a or path/b"""
        graph.rebuild()
        for key, values in kwargs.items():
            if not values:
                self.assertEqual(graph.node(path / key)['stale'], '')
            else:
                self.assertIn(graph.node(path / key)['stale'],
                              [str(path / char) for char in values])

    def test_rebuild(self):
        """Validate that the `rebuild()` method calculates the correct
        "stale" references"""
        with CliRunner().isolated_filesystem():
            graph = dependency.Graph()

            path = entry.Entry('path')
            a, b, c, d = [path / char for char in 'abcd']
            # (A, B) -> C -> D
            graph.add(c, a)
            graph.add(c, b)
            graph.add(d, c)

            # None of the files exist yet; A & B have no dependencies, so they
            # are stale due to themselves. C & D are stale due either A or B
            self.assert_rebuilt_state(graph, path,
                                      a='a', b='b', c='ab', d='ab')

            b.write(b'bbb')
            # B exists now, so dependency errors are only due to A now
            self.assert_rebuilt_state(graph, path, a='a', b='', c='a', d='a')

            a.write(b'aaa')
            # A exists now, too, so C is the bottleneck
            self.assert_rebuilt_state(graph, path, a='', b='', c='c', d='c')

            c.write(b'ccc')
            # Now there's only the final, self-reference
            self.assert_rebuilt_state(graph, path, a='', b='', c='', d='d')

            d.write(b'ddd')
            # Now no one is stale
            self.assert_rebuilt_state(graph, path, a='', b='', c='', d='')

            self._touch(a, 1000)
            # A's been updated. Need to run everything after it
            self.assert_rebuilt_state(graph, path, a='', b='', c='a', d='a')

            self._touch(d, 2000)
            self._touch(c, 3000)
            # C and D have been updated, but C's been updated after D
            self.assert_rebuilt_state(graph, path, a='', b='', c='', d='c')
