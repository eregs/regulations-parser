from datetime import date
import os
import shutil
import tempfile
from time import time
from unittest import TestCase

from regparser import eregs_index
from regparser.history.versions import Version


class SetupMixin(object):
    """Change the eregs_index.ROOT to a tempdir"""
    def setUp(self):
        self._original_root = eregs_index.ROOT
        eregs_index.ROOT = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(eregs_index.ROOT)
        eregs_index.ROOT = self._original_root


class VersionPathTests(SetupMixin, TestCase):
    def test_iterator(self):
        """Versions should be correctly linearized"""
        path = eregs_index.VersionPath("12", "1000")
        v1 = Version('1111', effective=date(2004, 4, 4),
                     published=date(2004, 4, 4))
        v2 = Version('2222', effective=date(2002, 2, 2),
                     published=date(2004, 4, 4))
        v3 = Version('3333', effective=date(2004, 4, 4),
                     published=date(2003, 3, 3))
        path.write(v1)
        path.write(v2)
        path.write(v3)

        self.assertEqual([v2, v3, v1], [v for v in path])


class DependencyGraphTests(SetupMixin, TestCase):
    def setUp(self):
        super(DependencyGraphTests, self).setUp()
        self.dgraph = eregs_index.DependencyGraph()
        self.path = eregs_index.Path("path")

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
