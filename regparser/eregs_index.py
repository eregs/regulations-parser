"""The eregs_index directory contains the output for many of the shell
commands. This module provides a quick interface to this index"""
import logging
import os
import shelve

from dagger import dagger
from lxml import etree


ROOT = ".eregs_index"


class Path(object):
    """Encapsulates access to a particular directory within the index"""
    def __init__(self, *dirs):
        self.path = os.path.join(ROOT, *dirs)

    def _create(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def write(self, label, content):
        self._create()
        path_str = os.path.join(self.path, label)
        with open(path_str, "w") as f:
            f.write(content)
            logging.info("Wrote {} to eregs_index".format(path_str))

    def read(self, label):
        self._create()
        with open(os.path.join(self.path, label)) as f:
            return f.read()

    def read_xml(self, label):
        return etree.fromstring(self.read(label))

    def __len__(self):
        return len(list(self.__iter__()))

    def __iter__(self):
        self._create()
        return (name for name in os.listdir(self.path))


class DependencyException(Exception):
    def __init__(self, key, dependency):
        super(DependencyException, self).__init__(
            "Missing dependency. {} is needed for {}".format(
                dependency, key))
        self.dependency = dependency
        self.key = key


class DependencyGraph(object):
    """Track dependencies between input and output files, storing them in
    `dependencies.db` for later retrieval. This lets us know that an output
    with dependencies needs to be updated if those dependencies have been
    updated"""
    def __init__(self):
        if not os.path.exists(ROOT):
            os.makedirs(ROOT)
        self.graph = shelve.open(os.path.join(ROOT, "dependencies.db"))
        self.dag = dagger()
        self._ran = False
        for key, dependencies in self.graph.items():
            self.dag.add(key, dependencies)

    def path_str(self, *file_path):
        return str(os.path.join(ROOT, *file_path))

    def add(self, output_tuple, input_tuple):
        """Add a dependency where output tuple relies on input_tuple"""
        self._ran = False
        from_str = self.path_str(*output_tuple)
        to_str = self.path_str(*input_tuple)

        deps = self.graph.get(from_str, set())
        deps.add(to_str)
        self.graph[from_str] = deps
        self.dag.add(from_str, [to_str])

    def _run_if_needed(self):
        if not self._ran:
            self.dag.run()
            self._ran = True

    def validate_for(self, *file_path):
        """Raise an exception if a particular output has stale dependencies"""
        self._run_if_needed()
        key = self.path_str(*file_path)
        for dependency in self.graph[key]:
            if self.dag.get(dependency).stale:
                raise DependencyException(key, dependency)

    def is_stale(self, *file_path):
        """Determine if a file needs to be rebuilt"""
        self._run_if_needed()
        key = self.path_str(*file_path)
        return bool(self.dag.get(key).stale)
