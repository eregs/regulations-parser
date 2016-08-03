import json
import logging
import os

from django.conf import settings
from lxml import etree

from regparser.history.versions import Version as VersionStruct
from regparser.notice.encoder import AmendmentEncoder
from regparser.notice.xml import NoticeXML
from regparser.tree.struct import (
    frozen_node_decode_hook, full_node_decode_hook, FullNodeEncoder)
from regparser.tree.xml_parser.xml_wrapper import XMLWrapper
from regparser.web.index.models import DependencyNode, Entry as DBEntry

logger = logging.getLogger(__name__)


class Entry(object):
    """Encapsulates an entry within the index. This could be a directory or a
    file"""
    PREFIX = None

    def __init__(self, *args):
        self.path = tuple(str(arg) for arg in args)

    def __div__(self, other):
        """Embellishment in the form of a DSL.
        Entry(1, 2, 3) / 4 / 5 == Entry(1, 2, 3, 4, 5)"""
        args = self.path + (other,)
        return self.__class__(*args)
    __truediv__ = __div__

    def __str__(self):
        prefix = settings.EREGS_INDEX_ROOT
        if self.PREFIX:
            prefix = os.path.join(prefix, self.PREFIX)
        return os.path.join(prefix, *self.path)

    def write(self, content):
        dep, _ = DependencyNode.objects.update_or_create(label=str(self))
        DBEntry.objects.update_or_create(label=dep, defaults={
            'contents': self.serialize(content)})
        logger.info("Wrote {}".format(str(self)))

    def serialize(self, content):
        """Default implementation; treat content as bytes"""
        return content

    def read(self):
        buffered_contents = DBEntry.objects.get(label=str(self)).contents
        # load it all into memory -- @todo optimization point
        return self.deserialize(bytes(buffered_contents))

    def deserialize(self, content):
        """Default implementation; treat the content as bytes"""
        return content

    def __iter__(self):
        """All sub-entries, i.e. the directory contents, as strings"""
        # @todo optimization point: use db indexes/similar to speed up this
        # query
        self_path = str(self)
        for entry in DBEntry.objects.filter(
                label__label__startswith=self_path):
            # Note: implicitly ordering by label in the DB model
            if os.path.dirname(entry.label_id) == self_path:
                yield os.path.basename(entry.label_id)

    def __len__(self):
        return len(list(self.__iter__()))

    def exists(self):
        return DBEntry.objects.filter(label=str(self)).exists()


class Notice(Entry):
    """Processes NoticeXMLs, keyed by notice_xml"""
    PREFIX = 'notice_xml'

    def serialize(self, content):
        return etree.tostring(content.xml, encoding='UTF-8')

    def deserialize(self, content):
        return NoticeXML(content, str(self))


class Annual(Entry):
    """Processes XML, keyed by annual"""
    PREFIX = 'annual'

    def serialize(self, content):
        return etree.tostring(content.xml, encoding='UTF-8')

    def deserialize(self, content):
        return XMLWrapper(content, str(self))


class Version(Entry):
    """Processes Versions, keyed by version"""
    PREFIX = 'version'

    def serialize(self, content):
        return content.json().encode('utf-8')

    def deserialize(self, content):
        return VersionStruct.from_json(content.decode('utf-8'))

    def __iter__(self):
        """Deserialize all Version objects we're aware of."""
        versions = [(self / path).read()
                    for path in super(Version, self).__iter__()]
        for version in sorted(versions):
            yield version.identifier


class FinalVersion(Version):
    """Like Version, but only list versions associated with final rules"""
    def __iter__(self):
        for version_id in super(FinalVersion, self).__iter__():
            version = (self / version_id).read()
            if version.is_final:
                yield version_id


class _JSONEntry(Entry):
    """Base class for importing/exporting JSON"""
    JSON_ENCODER = json.JSONEncoder
    JSON_DECODER = None

    def serialize(self, content):
        encoder = self.JSON_ENCODER(
            sort_keys=True, indent=4, separators=(', ', ': '))
        as_text = encoder.encode(content)
        return as_text.encode('utf-8')  # as bytes

    def deserialize(self, content):
        as_text = content.decode('utf-8')
        return json.loads(as_text, object_hook=self.JSON_DECODER)


class Tree(_JSONEntry):
    """Processes Nodes, keyed by tree"""
    PREFIX = 'tree'
    JSON_ENCODER = FullNodeEncoder
    JSON_DECODER = staticmethod(full_node_decode_hook)


class FrozenTree(Tree):
    """Like Tree, but decodes as FrozenNodes"""
    JSON_DECODER = staticmethod(frozen_node_decode_hook)


class SxS(_JSONEntry):
    """Processes Section-by-Section analyses, keyed by sxs"""
    PREFIX = 'sxs'
    JSON_ENCODER = AmendmentEncoder


class Layer(_JSONEntry):
    """Processes layers, keyed by layer"""
    PREFIX = 'layer'

    @classmethod
    def cfr(cls, *args):
        """Return a Layer entry in the appropriate namespace"""
        return cls("cfr", *args)

    @classmethod
    def preamble(cls, *args):
        """Return a Layer entry in the appropriate namespace"""
        return cls("preamble", *args)


class Diff(_JSONEntry):
    """Processes diffs, keyed by diff"""
    PREFIX = 'diff'


class Preamble(_JSONEntry):
    """Processes notice preambles, keyed by document id"""
    PREFIX = 'preamble'
    JSON_ENCODER = FullNodeEncoder
    JSON_DECODER = staticmethod(full_node_decode_hook)
