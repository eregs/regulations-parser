from contextlib import contextmanager
import os
from time import time
from unittest import TestCase

from click.testing import CliRunner

from regparser.index import dependency, entry


class DependencyGraphTests(TestCase):
    @contextmanager
    def dependency_graph(self):
        with CliRunner().isolated_filesystem():
            path = entry.Entry('path')
            self.depender = path / 'depender'
            self.dependency = path / 'dependency'
            yield dependency.Graph()

    def test_nonexistent_files_are_stale(self):
        """By definition, if a file is not present, it needs to be rebuilt"""
        with self.dependency_graph() as dgraph:
            self.dependency.write('value')
            dgraph.add(self.depender, self.dependency)
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))
            # shouldn't raise an exception; all dependencies are up to date
            dgraph.validate_for(self.depender)

    def test_nonexistant_deps_are_stale(self):
        """If a dependency is not present, we're stale"""
        with self.dependency_graph() as dgraph:
            self.depender.write('value')
            dgraph.add(self.depender, self.dependency)
            self.assertTrue(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))
            with self.assertRaises(dependency.Missing):
                dgraph.validate_for(self.depender)

    def test_updates_to_dependencies_flow(self):
        """If a dependency is updated, the graph should be recalculated"""
        with self.dependency_graph() as dgraph:
            self.dependency.write('value')
            self.depender.write('value2')
            dgraph.add(self.depender, self.dependency)
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertFalse(dgraph.is_stale(self.depender))

            # Set the update time of the dependency to the future
            os.utime(str(self.dependency),
                     (time()*1000 + 1000, time()*1000 + 1000))
            dgraph._ran = False
            dgraph._run_if_needed()
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))

    def test_dependencies_serialized(self):
        """Every instance of dependency.Graph shares a serialized copy of the
        dependencies"""
        with self.dependency_graph() as dgraph:
            dgraph.add(self.depender, self.dependency / '1')
            dgraph.add(self.depender, self.dependency / '2')
            self.assertItemsEqual(
                dgraph.dependencies(str(self.depender)),
                [str(self.dependency / 1), str(self.dependency / 2)])

            self.assertItemsEqual(
                dependency.Graph().dependencies(str(self.depender)),
                [str(self.dependency / 1), str(self.dependency / 2)])
