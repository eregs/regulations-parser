""" This module contains functions to help parse the changes in a notice.
Changes are the exact details of how the pargraphs, sections etc. in a
regulation have changed.  """

import copy
import logging
from collections import OrderedDict, namedtuple

from regparser.grammar import amdpar
from regparser.grammar.tokens import Verb
from regparser.layer.paragraph_markers import marker_of
from regparser.tree import struct
from regparser.tree.paragraph import p_levels

logger = logging.getLogger(__name__)
Change = namedtuple('Change', ['label_id', 'content'])


def node_to_dict(node):
    """ Convert a node to a dictionary representation. We skip the
    children, turning them instead into a list of labels instead. """
    if not hasattr(node, 'child_labels'):
        node.child_labels = [c.label_id() for c in node.children]

    node_dict = {}
    for k, v in node.__dict__.items():
        if k not in ('children', 'source_xml'):
            node_dict[k] = v
    return node_dict


def bad_label(node):
    """ Look through a node label, and return True if it's a badly formed
    label. We can do this because we know what type of character should up at
    what point in the label. """

    if node.node_type == struct.Node.REGTEXT:
        for i, l in enumerate(node.label):
            if i == 0 and not l.isdigit():
                return True
            elif i == 1 and not l.isdigit():
                return True
            elif i > 1 and l not in p_levels[i - 2]:
                return True
    return False


def impossible_label(n, amended_labels):
    """ Return True if n is not in the same family as amended_labels. """
    test = n.label_id().startswith
    return not any(filter(test, amended_labels))


def find_candidate(root, label_last, amended_labels):
    """
        Look through the tree for a node that has the same paragraph marker as
        the one we're looking for (and also has no children).  That might be a
        mis-parsed node. Because we're parsing partial sections in the notices,
        it's likely we might not be able to disambiguate between paragraph
        markers.
    """
    def check(node):
        """ Match last part of label."""
        if node.label[-1] == label_last:
            return node

    candidates = struct.walk(root, check)
    if len(candidates) > 1:
        # Look for mal-formed labels, labels that can't exist (because we're
        # not amending that part of the reg, or eventually a parent with no
        # children.

        bad_labels = [n for n in candidates if bad_label(n)]
        impossible_labels = [n for n in candidates
                             if impossible_label(n, amended_labels)]
        no_children = [n for n in candidates if n.children == []]

        # If we have a single option in any of the categories, return that.
        if len(bad_labels) == 1:
            return bad_labels
        elif len(impossible_labels) == 1:
            return impossible_labels
        elif len(no_children) == 1:
            return no_children
    return candidates


def resolve_candidates(amend_map, warn=True):
    """Ensure candidate isn't actually accounted for elsewhere, and fix
    it's label. """
    for label, nodes in list(amend_map.items()):
        for node in filter(lambda n: 'node' in n and n['candidate'], nodes):
            node_label = node['node'].label_id()
            if node_label not in amend_map:
                node['node'].label = label.split('-')
            elif label in amend_map:
                del amend_map[label]
                if warn:
                    mesg = 'Unable to match amendment to change for: %s'
                    logger.warning(mesg, label)


def find_misparsed_node(section_node, label, change, amended_labels):
    """ Nodes can get misparsed in the sense that we don't always know where
    they are in the tree or have their correct label. The first part
    corrects markerless labeled nodes by updating the node's label if
    the source text has been changed to include the markerless paragraph
    (ex. 123-44-p6 for paragraph 6). we know this because `label` here
    is parsed from that change. The second part uses label to find a
    candidate for a mis-parsed node and creates an appropriate change. """

    is_markerless = struct.Node.is_markerless_label(label)
    markerless_paragraphs = struct.filter_walk(
        section_node,
        struct.Node.is_markerless_label)
    if is_markerless and len(markerless_paragraphs) == 1:
        change['node'] = markerless_paragraphs[0]
        change['candidate'] = True
        return change

    candidates = find_candidate(section_node, label[-1], amended_labels)
    if len(candidates) == 1:
        candidate = candidates[0]
        change['node'] = candidate
        change['candidate'] = True
        return change


def match_labels_and_changes(amendments, section_node):
    """ Given the list of amendments, and the parsed section node, match the
    two so that we're only changing what's been flagged as changing. This helps
    eliminate paragraphs that are just stars for positioning, for example.  """
    amended_labels = [a.label_id() for a in amendments]

    amend_map = OrderedDict()
    for amend in amendments:
        existing = amend_map.get(amend.label_id(), [])
        change = {'action': amend.action, 'amdpar_xml': amend.amdpar_xml}
        if amend.field is not None:
            change['field'] = amend.field

        if amend.action == 'MOVE':
            change['destination'] = amend.destination
            amend_map[amend.label_id()] = existing + [change]
        elif amend.action == 'DELETE':
            amend_map[amend.label_id()] = existing + [change]
        elif section_node is not None:
            node = struct.find(section_node, amend.label_id())
            if node is None:
                candidate = find_misparsed_node(
                    section_node, amend.label, change, amended_labels)
                if candidate:
                    amend_map[amend.label_id()] = existing + [candidate]
            else:
                change['node'] = node
                change['candidate'] = False
                level2 = amend.tree_format_level2()
                if level2 and node.is_section():
                    change['parent_label'] = level2
                amend_map[amend.label_id()] = existing + [change]

    resolve_candidates(amend_map)
    return amend_map


def format_node(node, amendment, parent_label=None):
    """ Format a node into a dict, and add in amendment information. """
    node_as_dict = {
        'node': node_to_dict(node),
        'action': amendment['action'],
    }

    if 'extras' in amendment:
        node_as_dict.update(amendment['extras'])

    if 'field' in amendment:
        node_as_dict['field'] = amendment['field']
    if parent_label:
        node_as_dict['parent_label'] = parent_label
    return Change(node.label_id(), node_as_dict)


def create_field_amendment(label, amendment):
    """ If an amendment is changing just a field (text, title) then we
    don't need to package the rest of the paragraphs with it. Those get
    dealt with later, if appropriate. """

    nodes_list = []
    flatten_tree(nodes_list, amendment['node'])

    changed_nodes = [n for n in nodes_list if n.label_id() == label]
    nodes = [format_node(n, amendment) for n in changed_nodes]
    return nodes


def create_add_amendment(amendment, subpart_label=None):
    """ An amendment comes in with a whole tree structure. We break apart the
    tree here (this is what flatten does), convert the Node objects to JSON
    representations. This ensures that each amendment only acts on one node.
    In addition, this futzes with the change's field when stars are present.
    """

    nodes_list = []
    flatten_tree(nodes_list, amendment['node'])
    changes = []
    for node in nodes_list:
        is_root = node.label == amendment['node'].label
        if is_root:
            parent_label = amendment.get('parent_label')
        elif len(node.label) == 2:
            parent_label = subpart_label
        else:
            parent_label = None
        changes.append(format_node(node, amendment, parent_label))

    puts = [c for c in changes if c.content['action'] == 'PUT']
    for label, change in puts:
        node = struct.find(amendment['node'], label)
        text = node.text.strip()
        marker = marker_of(node)
        text = text[len(marker):].strip()
        # Text is stars, but this is not the root. Explicitly try to keep
        # this node
        if text == '* * *':
            change['action'] = Verb.KEEP

        # If text ends with a colon and is followed by stars, assume we are
        # only modifying the intro text
        if (text[-1:] == ':' and node.label == amendment['node'].label and
                node.source_xml is not None):
            following = node.source_xml.getnext()
            if following is not None and following.tag == 'STARS':
                change['field'] = '[text]'

    return changes


def create_reserve_amendment(amendment):
    """ Create a RESERVE related amendment. """
    return format_node(amendment['node'], amendment)


def create_subpart_amendment(subpart_node):
    """ Create an amendment that describes a subpart. In particular
    when the list of nodes added gets flattened, each node specifies which
    subpart it's part of. """

    amendment = {
        'node': subpart_node,
        'action': 'POST',
    }
    return create_add_amendment(amendment, subpart_node.label)


def flatten_tree(node_list, node):
    """ Flatten a tree, removing all hierarchical information, making a
    list out of all the nodes. """
    for c in node.children:
        flatten_tree(node_list, c)

    # Don't be destructive.
    no_kids = copy.deepcopy(node)
    no_kids.children = []
    node_list.append(no_kids)


class NoticeChanges(object):
    """ Notice changes. """
    def __init__(self):
        self._changes_by_xml = OrderedDict()

    def add_change(self, amdpar_xml, change):
        """ Track another change. This is cognizant of the fact that a single
        label can have more than one change. Do not add the same change twice
        (as may occur if both the parent and child are marked as added)"""
        existing = self[amdpar_xml].get(change.label_id, [])
        if change.content not in existing:
            existing.append(change.content)
        self[amdpar_xml][change.label_id] = existing

    def __getitem__(self, key):
        """Fetch changes by XML"""
        if key not in self._changes_by_xml:
            self._changes_by_xml[key] = OrderedDict()
        return self._changes_by_xml[key]


def fix_section_node(paragraphs, amdpar_xml):
    """ When notices are corrected, the XML for notices doesn't follow the
    normal syntax. Namely, pargraphs aren't inside section tags. We fix that
    here, by finding the preceding section tag and appending paragraphs to it.
    """

    sections = [s for s in amdpar_xml.itersiblings(preceding=True)
                if s.tag == 'SECTION']

    # Let's only do this if we find one section tag.
    if len(sections) == 1:
        section = copy.deepcopy(sections[0])
        for paragraph in paragraphs:
            section.append(copy.deepcopy(paragraph))
        return section


def find_subpart(amdpar_tag):
    """ Look amongst an amdpar tag's siblings to find a subpart. """
    for sibling in amdpar_tag.itersiblings():
        if sibling.tag == 'SUBPART':
            return sibling


def new_subpart_added(amendment):
    """ Return True if label indicates that a new subpart was added """
    new_subpart = amendment.action == 'POST'
    label = amendment.original_label
    m = [t for t, _, _ in amdpar.subpart_label.scanString(label)]
    return m and new_subpart
