from contextlib import contextmanager
from json import JSONEncoder
import hashlib
import re

from lxml import etree


class Node(object):
    APPENDIX = u'appendix'
    INTERP = u'interp'
    REGTEXT = u'regtext'
    SUBPART = u'subpart'
    EMPTYPART = u'emptypart'
    EXTRACT = u'extract'
    ALL_TYPES = (APPENDIX, INTERP, REGTEXT, SUBPART, EMPTYPART, EXTRACT)

    INTERP_MARK = 'Interp'

    MARKERLESS_REGEX = re.compile(r'p\d+')

    def __init__(self, text='', children=[], label=[], title=None,
                 node_type=REGTEXT, source_xml=None):

        self.text = unicode(text)

        # defensive copy
        self.children = list(children)

        self.label = [str(l) for l in label if l != '']
        title = unicode(title or '')
        self.title = title or None
        self.node_type = node_type
        self.source_xml = source_xml

    def __repr__(self):
        return (("Node( text = %s, children = %s, label = %s, title = %s, "
                + "node_type = %s)") % (repr(self.text), repr(self.children),
                repr(self.label), repr(self.title), repr(self.node_type)))

    def __cmp__(self, other):
        return cmp(repr(self), repr(other))

    def label_id(self):
        return '-'.join(self.label)

    def depth(self):
        """Inspect the label and type to determine the node's depth"""
        with node_type_cases(self.node_type) as cases:
            def default():
                return len(self.label)
            cases.appendix = cases.interp = default

            @cases.node_types
            def regtext_or_extract():
                if len(self.label) > 1:
                    #   Add one for the subpart level
                    return len(self.label) + 1
                else:
                    return default()

            @cases.node_types
            def subpart_or_emptypart():
                #   Subparts all on the same level
                return 2

        return cases.return_value

    @staticmethod
    def is_markerless_label(label):
        if not label:
            return None
        return re.match(Node.MARKERLESS_REGEX, label[-1])

    def is_markerless(self):
        return bool(self.is_markerless_label(self.label))

    def walk(self, per_node):
        walk(self, per_node)


class NodeTypeCases(object):
    def __init__(self, node_or_type):
        self.node_type = getattr(node_or_type, 'node_type', node_or_type)
        for node_type in Node.ALL_TYPES:
            setattr(self, node_type, None)

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, e_traceback):
        missing = self.missing_types()
        if missing:
            raise Exception("Missing types: %s", tuple(missing))
        else:
            self.return_value = getattr(self, self.node_type)()

    def missing_types(self):
        return [node_type for node_type in Node.ALL_TYPES
                if not callable(getattr(self, node_type))]

    def node_types(self, fn):
        for node_type in fn.func_name.split('_or_'):
            setattr(self, node_type, fn)

    def noop(self):
        pass


@contextmanager
def node_type_cases(node_or_type):
    with NodeTypeCases(node_or_type) as cases:
        yield cases


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
    FIELDS = set(['text', 'children', 'label', 'title', 'node_type',
                  'source_xml', 'tagged_text'])

    def default(self, obj):
        if isinstance(obj, Node):
            result = {field: getattr(obj, field, None)
                      for field in self.FIELDS}
            if obj.source_xml is not None:
                result['source_xml'] = etree.tostring(obj.source_xml)
            return result
        return super(FullNodeEncoder, self).default(obj)


def node_decode_hook(d):
    """Convert a JSON object into a Node"""
    if set(
            ('text', 'children',
                'label', 'node_type')) - set(d.keys()) == set():

        return Node(
            d['text'], d['children'], d['label'],
            d.get('title', None), d['node_type'])
    else:
        return d


def full_node_decode_hook(d):
    """Convert a JSON object into a full Node"""
    if set(d.keys()) == FullNodeEncoder.FIELDS:
        params = dict(d)
        del(params['tagged_text'])  # Ugly, but this field is set separately
        node = Node(**params)
        if d['tagged_text']:
            node.tagged_text = d['tagged_text']
        if node.source_xml:
            node.source_xml = etree.fromstring(node.source_xml)
        return node
    return d


def frozen_node_decode_hook(d):
    """Convert a JSON object into a FrozenNode"""
    if set(d.keys()) == FullNodeEncoder.FIELDS:
        params = dict(d)
        del(params['source_xml'])
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
    check = lambda n: n if predicate(n) else None
    response = walk(root, check)
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
    has_child = lambda n: any(c.label_id() == label for c in n.children)
    return find_first(root, has_child)


def join_text(node):
    """Join the text of this node and all children"""
    bits = []
    walk(node, lambda n: bits.append(n.text))
    return ''.join(bits)


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
        if root.label[-1] == Node.INTERP_MARK:
            is_child = lambda n: n.label[:len(root.label)-1] == root.label[:-1]
        else:
            is_child = lambda n: n.label[:len(root.label)] == root.label
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
        hasher.update(self.node_type)
        for child in self.children:
            hasher.update(child.hash)
        return hasher.hexdigest()

    def __hash__(self):
        """As the hash property is already distinctive, re-use it"""
        return hash(self.hash)

    def __eq__(self, other):
        """We define equality as having the same fields except for children.
        Instead of recursively inspecting them, we compare only their hash
        (this is a Merkle tree)"""
        return (other.__class__ == self.__class__
                and self.hash == other.hash
                # Compare the fields to limit the effect of hash collisions
                and self.text == other.text
                and self.title == other.title
                and self.node_type == other.node_type
                and self.tagged_text == other.tagged_text
                and self.label_id == other.label_id
                and [c.hash for c in self.children] ==
                    [c.hash for c in other.children])

    @staticmethod
    def from_node(node):
        """Convert a struct.Node (or similar) into a struct.FrozenNode. This
        also checks if this node has already been instantiated. If so, it
        returns the instantiated version (i.e. only one of each identical node
        exists in memory)"""
        children = map(FrozenNode.from_node, node.children)
        fresh = FrozenNode(text=node.text, children=children, label=node.label,
                           title=node.title or '', node_type=node.node_type,
                           tagged_text=getattr(node, 'tagged_text', '') or '')
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
