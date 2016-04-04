import logging
import os

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
    `dependencies.gml` for later retrieval. This lets us know that an output
    with dependencies needs to be updated if those dependencies have been
    updated"""
    GML_FILE = os.path.join(ROOT, "dependencies.gml")

    def __init__(self):
        if not os.path.exists(ROOT):
            os.makedirs(ROOT)

        if os.path.exists(self.GML_FILE):
            self._graph = networkx.read_gml(self.GML_FILE)
        else:
            self._graph = networkx.DiGraph()
        self._ran = False

    def add(self, output_entry, input_entry):
        """Add a dependency where output tuple relies on input_tuple"""
        self._ran = False
        from_str, to_str = str(output_entry), str(input_entry)

        self._graph.add_edge(to_str, from_str)
        networkx.write_gml(self._graph, self.GML_FILE)

    def __contains__(self, key):
        return key in self._graph

    def node(self, filename):
        if filename not in self._graph:
            self._graph.add_node(filename)
        return self._graph.node[filename]

    def dependencies(self, filename):
        if filename in self._graph:
            return self._graph.predecessors(filename)
        else:
            return []

    def roots(self):
        for node in self._graph:
            if not self.dependencies(node):
                yield(node)

    def derive_stale(self, filename, parent=None):
        modtime = self.node(filename).get('modtime')
        stale = self.node(filename).get('stale')
        if os.path.exists(filename):
            modtime = os.path.getmtime(filename)
        else:
            stale = filename

        if parent and modtime and self.node(parent)['modtime'] > modtime:
            stale = parent
        elif parent:
            stale = stale or self.node(parent)['stale']

        self.node(filename).update(modtime=modtime, stale=stale)

        for adj in self._graph[filename]:
            self.derive_stale(adj, filename)

    def _run_if_needed(self):
        if not self._ran:
            for root in self.roots():
                self.derive_stale(root)
            self._ran = True

    def validate_for(self, entry):
        """Raise an exception if a particular output has stale dependencies"""
        self._run_if_needed()
        key = str(entry)
        logger.debug("Validating dependencies for %r", key)
        for dependency in self.dependencies(key):
            if self.node(dependency).get('stale'):
                raise Missing(key, self.node(dependency)['stale'])

    def is_stale(self, entry):
        """Determine if a file needs to be rebuilt"""
        self._run_if_needed()
        return bool(self.node(str(entry)).get('stale'))
