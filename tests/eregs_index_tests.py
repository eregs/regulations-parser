import os
import shutil
import tempfile
from time import time
from unittest import TestCase

from regparser import eregs_index


class DependencyGraphTests(TestCase):
    def setUp(self):
        self._original_root = eregs_index.ROOT
        eregs_index.ROOT = tempfile.mkdtemp()

        self.dgraph = eregs_index.DependencyGraph()
        self.path = eregs_index.Path("path")

    def tearDown(self):
        shutil.rmtree(eregs_index.ROOT)
        eregs_index.ROOT = self._original_root

    def test_nonexistent_files_are_stale(self):
        """By definition, if a file is not present, it needs to be rebuilt"""
        self.path.write("dependency", "value")
        self.dgraph.add(("path", "depender"), ("path", "dependency"))
        self.assertFalse(self.dgraph.is_stale("path", "dependency"))
        self.assertTrue(self.dgraph.is_stale("path", "depender"))
        # shouldn't raise an exception; all dependencies are up to date
        self.dgraph.validate_for("path", "depender")

    def test_nonexistant_deps_are_stale(self):
        """If a dependency is not present, we're stale"""
        self.path.write("depender", "value")
        self.dgraph.add(("path", "depender"), ("path", "dependency"))
        self.assertTrue(self.dgraph.is_stale("path", "dependency"))
        self.assertTrue(self.dgraph.is_stale("path", "depender"))
        with self.assertRaises(eregs_index.DependencyException):
            self.dgraph.validate_for("path", "depender")

    def test_updates_to_dependencies_flow(self):
        """If a dependency is updated, the graph should be recalculated"""
        self.path.write("dependency", "value")
        self.path.write("depender", "value2")
        self.dgraph.add(("path", "depender"), ("path", "dependency"))
        self.assertFalse(self.dgraph.is_stale("path", "dependency"))
        self.assertFalse(self.dgraph.is_stale("path", "depender"))

        # Set the update time of the dependency to the future
        os.utime(os.path.join(eregs_index.ROOT, "path", "dependency"),
                 (time()*1000 + 1000, time()*1000 + 1000))
        self.dgraph.dag.run()
        self.assertFalse(self.dgraph.is_stale("path", "dependency"))
        self.assertTrue(self.dgraph.is_stale("path", "depender"))

    def test_dependencies_serialized(self):
        """Every instance of DependencyGraph shares a serialized copy of the
        dependencies"""
        self.dgraph.add(("path", "depender"), ("dependency", "1"))
        self.dgraph.add(("path", "depender"), ("dependency", "2"))
        self.assertEqual(
            self.dgraph.graph[self.dgraph.path_str("path", "depender")],
            set([self.dgraph.path_str("dependency", "1"),
                 self.dgraph.path_str("dependency", "2")]))

        del self.dgraph     # implicitly closing the database
        self.dgraph = eregs_index.DependencyGraph()
        self.assertEqual(
            self.dgraph.graph[self.dgraph.path_str("path", "depender")],
            set([self.dgraph.path_str("dependency", "1"),
                 self.dgraph.path_str("dependency", "2")]))
