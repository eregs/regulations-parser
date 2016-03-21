import json
import logging
import os

from regparser.history.versions import Version as VersionStruct
from regparser.notice.encoder import AmendmentEncoder
from regparser.notice.xml import NoticeXML
from regparser.tree.struct import (
    frozen_node_decode_hook, full_node_decode_hook, FullNodeEncoder)
from regparser.tree.xml_parser.xml_wrapper import XMLWrapper
from . import ROOT

logger = logging.getLogger(__name__)


class Entry(object):
    """Encapsulates an entry within the index. This could be a directory or a
    file"""
    PREFIX = (ROOT,)

    def __init__(self, *args):
        self.path = tuple(str(arg) for arg in args)

    def __div__(self, other):
        """Embellishment in the form of a DSL.
        Entry(1, 2, 3) / 4 / 5 == Entry(1, 2, 3, 4, 5)"""
        args = self.path + (other,)
        return self.__class__(*args)

    def __str__(self):
        return os.path.join(*(self.PREFIX + self.path))

    def _create_parent_dir(self):
        """Create the requisite directories if needed"""
        path = os.path.join(*(self.PREFIX + self.path[:-1]))
        if not os.path.exists(path):
            os.makedirs(path)

    def write(self, content):
        self._create_parent_dir()
        with open(str(self), "w") as f:
            f.write(self.serialize(content))
            logger.info("Wrote {}".format(str(self)))

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


class Notice(Entry):
    """Processes NoticeXMLs, keyed by notice_xml"""
    PREFIX = (ROOT, 'notice_xml')

    def serialize(self, content):
        return content.xml_str()

    def deserialize(self, content):
        return NoticeXML(content, str(self))


class Annual(Entry):
    """Processes XML, keyed by annual"""
    PREFIX = (ROOT, 'annual')

    def serialize(self, content):
        return content.xml_str()

    def deserialize(self, content):
        return XMLWrapper(content, str(self))


class Version(Entry):
    """Processes Versions, keyed by version"""
    PREFIX = (ROOT, 'version')

    def serialize(self, content):
        return content.json()

    def deserialize(self, content):
        return VersionStruct.from_json(content)

    def __iter__(self):
        """Deserialize all Version objects we're aware of."""
        versions = [(self / path).read()
                    for path in super(Version, self).__iter__()]
        for version in sorted(versions):
            yield version.identifier


class _JSONEntry(Entry):
    """Base class for importing/exporting JSON"""
    JSON_ENCODER = json.JSONEncoder
    JSON_DECODER = None

    def serialize(self, content):
        return self.JSON_ENCODER(
            sort_keys=True, indent=4, separators=(', ', ': ')).encode(content)

    def deserialize(self, content):
        return json.loads(content, object_hook=self.JSON_DECODER)


class Tree(_JSONEntry):
    """Processes Nodes, keyed by tree"""
    PREFIX = (ROOT, 'tree')
    JSON_ENCODER = FullNodeEncoder
    JSON_DECODER = staticmethod(full_node_decode_hook)


class FrozenTree(Tree):
    """Like Tree, but decodes as FrozenNodes"""
    JSON_DECODER = staticmethod(frozen_node_decode_hook)


class RuleChanges(_JSONEntry):
    """Processes notices, keyed by rule_changes"""
    PREFIX = (ROOT, 'rule_changes')
    JSON_ENCODER = AmendmentEncoder


class SxS(_JSONEntry):
    """Processes Section-by-Section analyses, keyed by sxs"""
    PREFIX = (ROOT, 'sxs')
    JSON_ENCODER = AmendmentEncoder


class Layer(_JSONEntry):
    """Processes layers, keyed by layer"""
    PREFIX = (ROOT, 'layer')

    @classmethod
    def cfr(cls, *args):
        """Return a Layer entry in the appropriate namespace"""
        return cls("cfr", *args)


class Diff(_JSONEntry):
    """Processes diffs, keyed by diff"""
    PREFIX = (ROOT, 'diff')


class Preamble(_JSONEntry):
    """Processes notice preambles, keyed by document id"""
    PREFIX = (ROOT, 'preamble')
    JSON_ENCODER = FullNodeEncoder
    JSON_DECODER = staticmethod(full_node_decode_hook)
