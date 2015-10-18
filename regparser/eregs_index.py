"""The eregs_index directory contains the output for many of the shell
commands. This module provides a quick interface to this index"""
import json
import logging
import os
import shelve

from dagger import dagger
from lxml import etree

from regparser.history.versions import Version
from regparser.notice.encoder import AmendmentEncoder
from regparser.notice.xml import NoticeXML
from regparser.tree.struct import full_node_decode_hook, FullNodeEncoder


ROOT = ".eregs_index"


class Entry(object):
    """Encapsulates an entry within the index. This could be a directory or a
    file"""
    PREFIX = (ROOT,)

    def __init__(self, *args):
        self._path = tuple(str(arg) for arg in args)

    def __div__(self, other):
        """Embellishment in the form of a DSL.
        Entry(1, 2, 3) / 4 / 5 == Entry(1, 2, 3, 4, 5)"""
        args = self._path + (other,)
        return self.__class__(*args)

    def __str__(self):
        return os.path.join(*(self.PREFIX + self._path))

    def _create_parent_dir(self):
        """Create the requisite directories if needed"""
        path = os.path.join(*(self.PREFIX + self._path[:-1]))
        if not os.path.exists(path):
            os.makedirs(path)

    def write(self, content):
        self._create_parent_dir()
        with open(str(self), "w") as f:
            f.write(self.serialize(content))
            logging.info("Wrote {}".format(str(self)))

    def serialize(self, content):
        """Default implementation; treat content as a string"""
        return content

    def read(self):
        self._create_parent_dir()
        with open(str(self)) as f:
            return self.deserialize(f.read())

    def deserialize(self, content):
        """Default implementation; treat the content as a string"""
        return content

    def __iter__(self):
        """All sub-entries, i.e. the directory contents, as strings"""
        if not os.path.exists(str(self)):
            return iter([])
        else:
            return iter(sorted(os.listdir(str(self))))

    def __len__(self):
        return len(list(self.__iter__()))


class NoticeEntry(Entry):
    """Processes NoticeXMLs, keyed by notice_xml"""
    PREFIX = (ROOT, 'notice_xml')

    def serialize(self, content):
        return content.xml_str()

    def deserialize(self, content):
        return NoticeXML(etree.fromstring(content))


class AnnualEntry(Entry):
    """Processes XML, keyed by annual"""
    PREFIX = (ROOT, 'annual')

    def serialize(self, content):
        return etree.tostring(content)

    def deserialize(self, content):
        return etree.fromstring(content)


class VersionEntry(Entry):
    """Processes Versions, keyed by version"""
    PREFIX = (ROOT, 'version')

    def serialize(self, content):
        return content.json()

    def deserialize(self, content):
        return Version.from_json(content)

    def __iter__(self):
        """Deserialize all Version objects we're aware of."""
        versions = [(self / path).read()
                    for path in super(VersionEntry, self).__iter__()]
        key = lambda version: (version.effective, version.published)
        for version in sorted(versions, key=key):
            yield version.identifier


class TreeEntry(Entry):
    """Processes Nodes, keyed by tree"""
    PREFIX = (ROOT, 'tree')

    def serialize(self, content):
        return FullNodeEncoder(sort_keys=True, indent=4,
                               separators=(', ', ': ')).encode(content)

    def deserialize(self, content):
        return json.loads(content, object_hook=full_node_decode_hook)


class RuleChangesEntry(Entry):
    """Processes notices, keyed by rule_changes"""
    PREFIX = (ROOT, 'rule_changes')

    def serialize(self, content):
        return AmendmentEncoder(sort_keys=True, indent=4,
                                separators=(', ', ': ')).encode(content)

    def deserialize(self, content):
        return json.loads(content)


class SxSEntry(RuleChangesEntry):
    """Processes Section-by-Section analyses, keyed by sxs"""
    PREFIX = (ROOT, 'sxs')


class LayerEntry(Entry):
    """Processes layers, keyed by layer"""
    PREFIX = (ROOT, 'layer')

    def serialize(self, content):
        return json.dumps(content)

    def deserialize(self, content):
        return json.loads(content)


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

    def add(self, output_entry, input_entry):
        """Add a dependency where output tuple relies on input_tuple"""
        self._ran = False
        from_str, to_str = str(output_entry), str(input_entry)

        deps = self.graph.get(from_str, set())
        deps.add(to_str)
        self.graph[from_str] = deps
        self.dag.add(from_str, [to_str])

    def _run_if_needed(self):
        if not self._ran:
            self.dag.run()
            self._ran = True

    def validate_for(self, entry):
        """Raise an exception if a particular output has stale dependencies"""
        self._run_if_needed()
        key = str(entry)
        for dependency in self.graph[key]:
            if self.dag.get(dependency).stale:
                raise DependencyException(key, dependency)

    def is_stale(self, entry):
        """Determine if a file needs to be rebuilt"""
        self._run_if_needed()
        return bool(self.dag.get(str(entry)).stale)
