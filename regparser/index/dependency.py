import logging

from django.db import transaction
from django.utils import timezone
import networkx

from regparser.web.index.models import (
    Dependency, DependencyNode, Entry as DBEntry)


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

    def __init__(self):
        self.deserialize()
        self.rebuild()

    @transaction.atomic
    def serialize(self):
        """Convert the in-memory self._graph into db records"""
        Dependency.objects.all().delete()

        new_vertices = set(self._graph.nodes()) - set(
            node.label for node in DependencyNode.objects.all())
        DependencyNode.objects.bulk_create(
            DependencyNode(label=label) for label in new_vertices)

        Dependency.objects.bulk_create(
            Dependency(depender_id=depender, target_id=target)
            for (depender, target) in self._graph.edges())

    @transaction.atomic
    def deserialize(self):
        """Convert db records into the in-memory self._graph"""
        self._graph = networkx.DiGraph()
        self._graph.add_nodes_from(
            n.label for n in DependencyNode.objects.all())
        self._graph.add_edges_from(
            (e.depender_id, e.target_id)
            for e in Dependency.objects.all())

    def add(self, output_entry, input_entry):
        """Add a dependency where output tuple relies on input_tuple"""
        self._graph.add_edge(str(input_entry), str(output_entry))
        self.rebuild()
        self.serialize()    # @todo: make this incremental

    def __contains__(self, key):
        """Does the graph contain a particular node?"""
        return str(key) in self._graph

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
            entry = DBEntry.objects.filter(label_id=node).first()
            if entry:
                modtime = entry.modified
                stale = ''
            else:
                modtime = timezone.now()
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

    def clear_for(self, entry):
        """Remove all dependencies for a particular entry"""
        key = str(entry)
        for dependency in self.dependencies(key):
            return self._graph.remove_edge(dependency, key)
        self.rebuild()
        self.serialize()    # @todo: incremental
