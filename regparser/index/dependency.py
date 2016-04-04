import logging
import os
from time import time

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
        self.rebuild()

    def add(self, output_entry, input_entry):
        """Add a dependency where output tuple relies on input_tuple"""
        self._graph.add_edge(str(input_entry), str(output_entry))
        self.rebuild()
        networkx.write_gml(self._graph, self.GML_FILE)

    def __contains__(self, key):
        """Does the graph contain a particular node?"""
        return key in self._graph

    def node(self, filename):
        """Get node attributes for a specific filename. If the node isn't
        present, create it"""
        filename = str(filename)
        if filename not in self._graph:
            self._graph.add_node(filename)
        return self._graph.node[filename]

    def dependencies(self, filename):
        """What does other nodes does this filename *directly* depend on?"""
        filename = str(filename)
        if filename in self._graph:
            return self._graph.predecessors(filename)
        else:
            return []

    def rebuild(self):
        """Scan the modification times of all the nodes in the graph to
        determine what's been updated. We mark nodes "stale" if one of their
        dependencies has been updated since the depending node was built. Use
        topological sort to make sure we process dependencies first."""
        for node in networkx.topological_sort(self._graph):
            if os.path.exists(node):
                modtime = os.path.getmtime(node)
                stale = ''
            else:
                modtime = time()
                stale = node

            # Check immediate dependencies (which were updated in a previous
            # step)
            for dependency in self.dependencies(node):
                if self.node(dependency)['modtime'] > modtime:
                    stale = dependency
                else:
                    stale = self.node(dependency)['stale'] or stale

            self.node(node).update(modtime=modtime, stale=stale)

    def validate_for(self, entry):
        """Raise an exception if a particular output has stale dependencies"""
        key = str(entry)
        logger.debug("Validating dependencies for %r", key)
        for dependency in self.dependencies(key):
            if self.node(dependency).get('stale'):
                raise Missing(key, self.node(dependency)['stale'])

    def is_stale(self, entry):
        """Determine if a file needs to be rebuilt"""
        return bool(self.node(str(entry)).get('stale'))
