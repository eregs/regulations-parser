from contextlib import contextmanager
import logging
import os
import shelve

import networkx

from . import ROOT


logger = logging.getLogger(__name__)


class Missing(Exception):
    def __init__(self, key, dependency):
        super(Missing, self).__init__(
            "Missing dependency. {} is needed for {}".format(
                dependency, key))
        self.dependency = dependency
        self.key = key


class Graph(object):
    """Track dependencies between input and output files, storing them in
    `dependencies.db` for later retrieval. This lets us know that an output
    with dependencies needs to be updated if those dependencies have been
    updated"""
    DB_FILE = os.path.join(ROOT, "dependencies.db")

    def __init__(self):
        if not os.path.exists(ROOT):
            os.makedirs(ROOT)
        self.graph = networkx.DiGraph()
        self._ran = False

        with self.dependency_db() as db:
            for key, dependencies in db.items():
                self.graph.add_edges_from((d, key) for d in dependencies)

    @contextmanager
    def dependency_db(self):
        """Python 2 doesn't have a context manager for shelve.open, so we've
        created one"""
        db = shelve.open(self.DB_FILE)
        try:
            yield db
        finally:
            db.close()

    def add(self, output_entry, input_entry):
        """Add a dependency where output tuple relies on input_tuple"""
        self._ran = False
        from_str, to_str = str(output_entry), str(input_entry)

        self.graph.add_edge(to_str, from_str)
        with self.dependency_db() as db:
            deps = db.get(from_str, set())
            deps.add(to_str)
            db[from_str] = deps

    def derive_stale(self, filename, parent=None):
        modtime = self.graph.node[filename].get('modtime')
        stale = self.graph.node[filename].get('stale', False)
        if os.path.exists(filename):
            modtime = os.path.getmtime(filename)
        else:
            stale = True

        if (parent and modtime and
                self.graph.node[parent]['modtime'] > modtime):
            stale = True
        elif parent:
            stale = stale or self.graph.node[parent]['stale']

        self.graph.node[filename]['modtime'] = modtime
        self.graph.node[filename]['stale'] = stale

        for adj in self.graph[filename]:
            self.derive_stale(adj, filename)

    def _run_if_needed(self):
        if not self._ran:
            for node in self.graph:
                if not self.graph.predecessors(node):
                    self.derive_stale(node)
            self._ran = True

    def validate_for(self, entry):
        """Raise an exception if a particular output has stale dependencies"""
        self._run_if_needed()
        key = str(entry)
        logger.debug("Validating dependencies for %r", key)
        with self.dependency_db() as db:
            for dependency in db[key]:
                if self.graph.node[dependency].get('stale'):
                    raise Missing(key, dependency)

    def is_stale(self, entry):
        """Determine if a file needs to be rebuilt"""
        self._run_if_needed()
        return bool(self.graph.node[str(entry)].get('stale'))
