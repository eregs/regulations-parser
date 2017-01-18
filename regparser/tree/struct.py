import hashlib
import re
from json import JSONEncoder

import six
from lxml import etree

from regparser.tree.depth.markers import MARKERLESS


class Node(object):
    APPENDIX = u'appendix'
    INTERP = u'interp'
    REGTEXT = u'regtext'
    SUBPART = u'subpart'
    EMPTYPART = u'emptypart'
    EXTRACT = u'extract'
    NOTE = u'note'

    INTERP_MARK = 'Interp'

    MARKERLESS_REGEX = re.compile(r'p\d+')

    def __init__(self, text='', children=None, label=None, title=None,
                 node_type=REGTEXT, source_xml=None, tagged_text=''):
        if children is None:
            children = []
        if label is None:
            label = []

        self.text = six.text_type(text)

        # defensive copy
        self.children = list(children)

        self.label = [str(l) for l in label if l != '']
        title = six.text_type(title or '')
        self.title = title or None
        self.node_type = node_type
        self.source_xml = source_xml
        self.tagged_text = tagged_text

    def __repr__(self):
        text = ("Node(text={0}, children={1}, label={2}, title={3}, "
                "node_type={4})")
        return text.format(
            repr(self.text), repr(self.children), repr(self.label),
            repr(self.title), repr(self.node_type)
        )

    def __lt__(self, other):
        return repr(self) < repr(other)

    def __eq__(self, other):
        return repr(self) == repr(other)

    @property
    def cfr_part(self):
        if self.label:
            return self.label[0]

    def label_id(self):
        return '-'.join(self.label)

    def depth(self):
        """Inspect the label and type to determine the node's depth"""
        second = (self.label[1:2] or [""])[0]
        second_is_digit = second[:1].isdigit()
        is_interp = self.INTERP_MARK in self.label
        is_root = len(self.label) <= 1
        if self.node_type in (self.SUBPART, self.EMPTYPART):
            #   Subparts all on the same level
            return 2
        elif not second_is_digit or is_root or is_interp:
            return len(self.label)
        else:
            #   Add one for the subpart level
            return len(self.label) + 1

    @classmethod
    def is_markerless_label(cls, label):
        if not label:
            return None
        return (cls.MARKERLESS_REGEX.match(label[-1]) or
                label[-1] == MARKERLESS)

    def is_markerless(self):
        return bool(self.is_markerless_label(self.label))

    def is_section(self):
        """Sections are contained within subparts/subject groups. They are not
        part of the appendix"""
        return len(self.label) == 2 and self.label[1][:1].isdigit()

    def walk(self, fn):
        """See walk(node, fn)"""
        return walk(self, fn)


class NodeEncoder(JSONEncoder):
    """Custom JSON encoder to handle Node objects"""
    def default(self, obj):
        if isinstance(obj, Node):
            fields = dict(obj.__dict__)
            if obj.title is None:
                del fields['title']
            for field in ('tagged_text', 'source_xml', 'child_labels'):
                if field in fields:
                    del fields[field]
            return fields
        return super(NodeEncoder, self).default(obj)


class FullNodeEncoder(JSONEncoder):
    """Encodes Nodes into JSON, not losing any of the fields"""
    FIELDS = {'text', 'children', 'label', 'title', 'node_type', 'source_xml',
              'tagged_text'}

    def default(self, obj):
        if isinstance(obj, Node):
            result = {field: getattr(obj, field, None)
                      for field in self.FIELDS}
            if obj.source_xml is not None:
                result['source_xml'] = etree.tounicode(obj.source_xml)
            return result
        return super(FullNodeEncoder, self).default(obj)


def full_node_decode_hook(d):
    """Convert a JSON object into a full Node"""
    if set(d.keys()) == FullNodeEncoder.FIELDS:
        params = dict(d)
        node = Node(**params)
        if node.source_xml:
            node.source_xml = etree.fromstring(node.source_xml)
        return node
    return d


def frozen_node_decode_hook(d):
    """Convert a JSON object into a FrozenNode"""
    if set(d.keys()) == FullNodeEncoder.FIELDS:
        params = dict(d)
        del params['source_xml']
        fresh = FrozenNode(**params)
        return fresh.prototype()
    return d


def walk(node, fn):
    """Perform fn for every node in the tree. Pre-order traversal. fn must
    be a function that accepts a root node."""
    result = fn(node)

    if result is not None:
        results = [result]
    else:
        results = []
    for child in node.children:
        results += walk(child, fn)
    return results


def filter_walk(node, fn):
    """Perform fn on the label for every node in the tree and return a
    list of nodes on which the function returns truthy."""
    return walk(node, lambda n: n if fn(n.label) else None)


def find_first(root, predicate):
    """Walk the tree and find the first node which matches the predicate"""
    response = walk(root, lambda n: n if predicate(n) else None)
    if response:
        return response[0]


def find(root, label):
    """Search through the tree to find the node with this label."""
    if isinstance(label, Node):
        label = label.label_id()
    return find_first(root, lambda n: n.label_id() == label)


def find_parent(root, label):
    """Search through the tree to find the _parent_ or a node with this
    label."""
    if isinstance(label, Node):
        label = label.label_id()

    def has_child(n):
        return any(c.label_id() == label for c in n.children)

    return find_first(root, has_child)


def merge_duplicates(nodes):
    """Given a list of nodes with the same-length label, merge any
    duplicates (by combining their children)"""
    found_pair = None
    for lidx, lhs in enumerate(nodes):
        for ridx, rhs in enumerate(nodes[lidx + 1:], lidx + 1):
            if lhs.label == rhs.label:
                found_pair = (lidx, ridx)
    if found_pair:
        lidx, ridx = found_pair
        lhs, rhs = nodes[lidx], nodes[ridx]
        lhs.children.extend(rhs.children)
        return merge_duplicates(nodes[:ridx] + nodes[ridx + 1:])
    else:
        return nodes


def treeify(nodes):
    """Given a list of nodes, convert those nodes into the appropriate tree
    structure based on their labels. This assumes that all nodes will fall
    under a set of 'root' nodes, which have the min-length label."""
    if not nodes:
        return nodes

    min_len, with_min = len(nodes[0].label), []

    for node in nodes:
        if len(node.label) == min_len:
            with_min.append(node)
        elif len(node.label) < min_len:
            min_len = len(node.label)
            with_min = [node]
    with_min = merge_duplicates(with_min)

    roots = []
    for root in with_min:
        label = root.label
        if root.label[-1] == Node.INTERP_MARK:
            label = root.label[:-1]

        def is_child(node):
            return node.label[:len(label)] == label
        children = [n for n in nodes if n.label != root.label and is_child(n)]
        root.children = root.children + treeify(children)
        roots.append(root)
    return roots


class FrozenNode(object):
    """Immutable interface for nodes. No guarantees about internal state."""
    _pool = {}    # collection of all FrozenNodes, keyed by hash

    def __init__(self, text='', children=(), label=(), title='',
                 node_type=Node.REGTEXT, tagged_text=''):
        self._text = text or ''
        self._children = tuple(children)
        self._label = tuple(label)
        self._title = title or ''
        self._node_type = node_type
        self._tagged_text = tagged_text or ''
        self._child_labels = tuple(c.label_id for c in self.children)
        self._label_id = '-'.join(self.label)
        self._hash = self._generate_hash()
        if self.hash not in FrozenNode._pool:
            FrozenNode._pool[self.hash] = self

    @property
    def text(self):
        return self._text

    @property
    def children(self):
        return self._children

    @property
    def label(self):
        return self._label

    @property
    def title(self):
        return self._title

    @property
    def node_type(self):
        return self._node_type

    @property
    def tagged_text(self):
        return self._tagged_text

    @property
    def hash(self):
        return self._hash

    @property
    def label_id(self):
        return self._label_id

    @property
    def child_labels(self):
        return self._child_labels

    def _generate_hash(self):
        """Called during instantiation. Digests all fields"""
        hasher = hashlib.sha256()
        hasher.update(self.text.encode('utf-8'))
        hasher.update(self.tagged_text.encode('utf-8'))
        hasher.update(self.title.encode('utf-8'))
        hasher.update(self.label_id.encode('utf-8'))
        hasher.update(self.node_type.encode('utf-8'))
        for child in self.children:
            hasher.update(child.hash.encode('utf-8'))
        return hasher.hexdigest()

    def __hash__(self):
        """As the hash property is already distinctive, re-use it"""
        return hash(self.hash)

    def __eq__(self, other):
        """We define equality as having the same fields except for children.
        Instead of recursively inspecting them, we compare only their hash
        (this is a Merkle tree)"""
        return (other.__class__ == self.__class__ and
                self.hash == other.hash and
                # Compare the fields to limit the effect of hash collisions
                self.text == other.text and
                self.title == other.title and
                self.node_type == other.node_type and
                self.tagged_text == other.tagged_text and
                self.label_id == other.label_id and
                [c.hash for c in self.children] ==
                [c.hash for c in other.children])

    @staticmethod
    def from_node(node):
        """Convert a struct.Node (or similar) into a struct.FrozenNode. This
        also checks if this node has already been instantiated. If so, it
        returns the instantiated version (i.e. only one of each identical node
        exists in memory)"""
        children = [FrozenNode.from_node(n) for n in node.children]
        fresh = FrozenNode(text=node.text, children=children, label=node.label,
                           title=node.title or '', node_type=node.node_type,
                           tagged_text=node.tagged_text)
        return fresh.prototype()

    # @todo - seems like something we could implement via __new__?
    def prototype(self):
        """When we instantiate a FrozenNode, we add it to _pool if we've not
        seen an identical FrozenNode before. If we have, we want to work with
        that previously seen version instead. This method returns the _first_
        FrozenNode with identical fields"""
        return FrozenNode._pool[self.hash]  # note this may not be self

    def clone(self, **kwargs):
        """Implement a namedtuple `_replace` style functionality, copying all
        fields that aren't explicitly replaced."""
        for field in ('text', 'children', 'label', 'title', 'node_type',
                      'tagged_text'):
            kwargs[field] = kwargs.get(field, getattr(self, field))
        fresh = FrozenNode(**kwargs)
        return fresh.prototype()
