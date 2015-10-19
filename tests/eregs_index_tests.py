from contextlib import contextmanager
from datetime import date
import os
from time import time
from unittest import TestCase

from click.testing import CliRunner

from regparser import eregs_index
from regparser.history.versions import Version


class VersionEntryTests(TestCase):
    def test_iterator(self):
        """Versions should be correctly linearized"""
        with CliRunner().isolated_filesystem():
            path = eregs_index.VersionEntry("12", "1000")
            v1 = Version('1111', effective=date(2004, 4, 4),
                         published=date(2004, 4, 4))
            v2 = Version('2222', effective=date(2002, 2, 2),
                         published=date(2004, 4, 4))
            v3 = Version('3333', effective=date(2004, 4, 4),
                         published=date(2003, 3, 3))
            (path / '1111').write(v1)
            (path / '2222').write(v2)
            (path / '3333').write(v3)

            self.assertEqual(['2222', '3333', '1111'], list(path))


class DependencyGraphTests(TestCase):
    @contextmanager
    def dependency_graph(self):
        with CliRunner().isolated_filesystem():
            path = eregs_index.Entry('path')
            self.depender = path / 'depender'
            self.dependency = path / 'dependency'
            yield eregs_index.DependencyGraph()

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
            with self.assertRaises(eregs_index.DependencyException):
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
            dgraph.dag.run()
            self.assertFalse(dgraph.is_stale(self.dependency))
            self.assertTrue(dgraph.is_stale(self.depender))

    def test_dependencies_serialized(self):
        """Every instance of DependencyGraph shares a serialized copy of the
        dependencies"""
        with self.dependency_graph() as dgraph:
            dgraph.add(self.depender, self.dependency / '1')
            dgraph.add(self.depender, self.dependency / '2')
            self.assertEqual(
                dgraph.graph[str(self.depender)],
                set([str(self.dependency / 1), str(self.dependency / 2)]))

            del dgraph     # implicitly closing the database
            dgraph = eregs_index.DependencyGraph()
            self.assertEqual(
                dgraph.graph[str(self.depender)],
                set([str(self.dependency / 1), str(self.dependency / 2)]))
