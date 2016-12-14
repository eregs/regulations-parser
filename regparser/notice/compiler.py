""" Notices indicate how a regulation has changed since the last version. This
module contains code to compile a regulation from a notice's changes. """

import copy
import logging
import re
from bisect import bisect
from collections import defaultdict

from roman import fromRoman

from regparser.grammar.tokens import Verb
from regparser.layer.paragraph_markers import marker_of
from regparser.tree.struct import Node, find, find_parent

logger = logging.getLogger(__name__)


def get_parent_label(node):
    """ Given a node, get the label of it's parent. """
    if node.node_type == Node.SUBPART:
        return node.label[0]
    elif node.node_type == Node.INTERP:
        marker_position = node.label.index(Node.INTERP_MARK)
        interpreting = node.label[:marker_position]
        comment_pars = node.label[marker_position + 1:]
        if comment_pars:                # 111-3-a-Interp-4-i
            return '-'.join(node.label[:-1])
        elif len(interpreting) > 1:     # 111-3-a-Interp
            return '-'.join(interpreting[:-1] + [Node.INTERP_MARK])
        else:                           # 111-Interp
            return node.label[0]
    else:
        parent_label = node.label[:-1]
        return '-'.join(parent_label)


_component_re = re.compile('[a-z]+|[A-Z]+|[0-9]+')


def make_label_sortable(label, roman=False):
    """ Make labels sortable, but converting them as appropriate.
    For example, "45Ai33b" becomes (45, "A", "i", 33, "b").
    Also, appendices have labels that look like 30(a), we make those
    appropriately sortable. """
    if roman:
        return (fromRoman(label.upper()),)
    segments = _component_re.findall(label)
    return tuple(int(seg) if seg.isdigit() else seg for seg in segments)


def make_root_sortable(label, node_type):
    """ Child nodes of the root contain nodes of various types, these
    need to be sorted correctly. This returns a tuple to help
    sort these first level nodes. """

    if node_type == Node.SUBPART or node_type == Node.EMPTYPART:
        return (0, label[-1])
    elif node_type == Node.APPENDIX:
        return (1, label[-1])
    elif node_type == Node.INTERP:
        return (2,)


def replace_first_sentence(text, replacement):
    """ Replace the first sentence in text with replacement. This makes
    some incredibly simplifying assumptions - so buyer beware. """
    no_periods_replacement = replacement.replace('.', '')

    sentences = text.split('.', 1)
    if len(sentences) > 1:
        sentences[0] = no_periods_replacement
        return '.'.join(sentences)
    else:
        return replacement


def node_text_equality(left, right):
    """Do these two nodes have the same text fields? Accounts for Nones"""
    return (
        left and right and
        left.text == right.text and
        left.title == right.title and
        left.tagged_text == right.tagged_text
    )


def overwrite_marker(origin, new_label):
    """ The node passed in has a label, but we're going to give it a
    new one (new_label). This is necessary during node moves.  """
    marker = marker_of(origin)
    if '(' in marker:
        origin.text = origin.text.replace(marker, '({0})'.format(new_label), 1)
    elif marker:
        origin.text = origin.text.replace(marker, '{0}.'.format(new_label), 1)
    else:
        logger.warning("Cannot replace marker in %s", origin.text)

    return origin


def is_reserved_node(node):
    """ Return true if the node is reserved. """
    reserved_title = node.title and '[Reserved]' in node.title
    reserved_text = node.text and '[Reserved]' in node.text
    return reserved_title or reserved_text


def is_interp_placeholder(node):
    """Interpretations may have nodes that exist purely to enforce
    structure. Knowing if a node is such a placeholder makes it easier to
    know if a POST should really just modify the existing placeholder."""
    return (Node.INTERP_MARK in node.label and not node.text and
            not node.title)


class RegulationTree(object):
    """ This encapsulates a regulation tree, and methods to change that tree.
    """

    def __init__(self, previous_tree):
        self.tree = copy.deepcopy(previous_tree)
        self._kept__by_parent = defaultdict(list)

    def keep(self, labels):
        """The 'KEEP' verb tells us that a node should not be removed
        (generally because it would had we dropped the children of its
        parent). "Keeping" those nodes makes sure they do not disappear when
        editing their parent"""
        for label in labels:
            node = self.find_node(label)
            parent_label = get_parent_label(node)
            self._kept__by_parent[parent_label].append(node)

    def get_parent(self, node):
        """ Get the parent of a node. Returns None if parent not found. """
        parent = find_parent(self.tree, node)
        if not parent:  # e.g. because the node doesn't exist in the tree yet
            parent_label_id = get_parent_label(node)
            parent = find(self.tree, parent_label_id)
        if not parent:
            logger.error("Could not find parent of %s. Misparsed amendment?",
                         node.label_id())
        return parent

    def add_to_root(self, node):
        """ Add a child to the root of the tree. """
        self.tree.children.append(node)

        for c in self.tree.children:
            c.sortable = make_root_sortable(c.label, c.node_type)

        self.tree.children.sort(key=lambda x: x.sortable)

        for c in self.tree.children:
            del c.sortable

    @staticmethod
    def add_child(children, node, order=None):
        """ Add a child to the children, and sort appropriately. This is used
        for non-root nodes. """
        if order is None:
            order = []

        children = children + [node]    # non-destructive
        child_labels = {c.label_id() for c in children}

        if child_labels.issubset(set(order)):
            lookup = {c.label_id(): c for c in children}
            return [lookup[label_id] for label_id in order
                    if label_id in child_labels]
        else:   # Must guess at the appropriate order
            sort_order = []
            for c in children:
                if c.label[-1] == Node.INTERP_MARK:
                    sort_order.append((2,) + make_label_sortable(
                        c.label[-2], roman=(len(c.label) == 6)))
                elif Node.INTERP_MARK in c.label:
                    marker_idx = c.label.index(Node.INTERP_MARK)
                    comment_pars = c.label[marker_idx + 1:]
                    sort_order.append((1,) + make_label_sortable(
                        comment_pars[-1], roman=(len(comment_pars) == 2)))
                elif c.node_type == Node.APPENDIX:
                    sort_order.append(make_label_sortable(c.label[-1], False))
                elif c.node_type == Node.EMPTYPART:
                    sort_order.append((0,))
                else:
                    sort_order.append(make_label_sortable(
                        c.label[-1], roman=(len(c.label) == 5)))

            new_el_sort = sort_order[-1]
            sort_order = sort_order[:-1]
            # Use bisect so the whole list isn't resorted (the original list
            # may not be strictly sorted)
            insert_idx = bisect(sort_order, new_el_sort)
            return children[:insert_idx] + [node] + children[insert_idx:-1]

    def delete_from_parent(self, node):
        """ Delete node from it's parent, effectively removing it from the
        tree. """

        parent = self.get_parent(node)
        other_children = [c for c in parent.children if c.label != node.label]
        parent.children = other_children

    def delete(self, label_id):
        """ Delete the node with label_id from the tree. """
        node = find(self.tree, label_id)
        if node is None:
            logger.warning("Attempting to delete %s failed", label_id)
        else:
            self.delete_from_parent(node)

    def reserve(self, label_id, node):
        """ Reserve either an existing node (by replacing it) or
        reserve by adding a new node. When a node is reserved, it's
        represented in the FR XML. We simply use that representation here
        instead of doing something else. """

        existing_node = find(self.tree, label_id)
        if existing_node is None:
            self.add_node(node)
        else:
            self.replace_node_and_subtree(node)

    def move(self, origin, destination):
        """ Move a node from one part in the tree to another. """
        origin = find(self.tree, origin)
        self.delete_from_parent(origin)

        origin = overwrite_marker(origin, destination[-1])
        origin.label = destination
        self.add_node(origin)

    def replace_node_and_subtree(self, node):
        """ Replace an existing node in the tree with node. """

        parent = self.get_parent(node)

        prev_idx = [idx for idx, c in enumerate(parent.children)
                    if c.label == node.label]
        if prev_idx:
            # replace existing element in place
            prev_idx = prev_idx[0]
            parent.children = (parent.children[:prev_idx] + [node] +
                               parent.children[prev_idx + 1:])
        else:
            # actually adding a new element
            parent.children = self.add_child(parent.children, node,
                                             getattr(parent, 'child_labels',
                                                     []))

        # Finally, we see if this node is the parent of any 'kept' children.
        # If so, add them back
        label_id = node.label_id()
        if label_id in self._kept__by_parent:
            for kept in self._kept__by_parent[label_id]:
                node.children = self.add_child(node.children, kept,
                                               getattr(node, 'child_labels',
                                                       []))

    def create_empty_node(self, node_label):
        """ In rare cases, we need to flush out the tree by adding
        an empty node. Returns the created node"""
        node_label = node_label.split('-')
        if Node.INTERP_MARK in node_label:
            node_type = Node.INTERP
        elif len(node_label) > 1 and not node_label[1].isdigit():
            node_type = Node.APPENDIX
        else:
            node_type = Node.REGTEXT
        node = Node(label=node_label, node_type=node_type)
        parent = self.get_parent(node)
        if not parent:
            parent = self.create_empty_node(get_parent_label(node))
        parent.children = self.add_child(parent.children, node,
                                         getattr(parent, 'child_labels', []))
        return node

    def contains(self, label):
        """Is this label already in the tree? label can be a list or a
        string"""
        return bool(self.find_node(label))

    def find_node(self, label):
        if isinstance(label, list):
            label = '-'.join(label)
        return find(self.tree, label)

    def add_node(self, node, parent_label=None):
        """ Add an entirely new node to the regulation tree. Accounts for
        placeholders, reserved nodes, """
        existing = find(self.tree, node.label_id())
        if existing and is_reserved_node(existing):
            logger.warning('Replacing reserved node: %s', node.label_id())
            return self.replace_node_and_subtree(node)
        elif existing and is_interp_placeholder(existing):
            existing.title = node.title
            existing.text = node.text
            existing.tagged_text = node.tagged_text
        # Proceed only if we're not re-adding an existing node (common in our
        # messy data)
        elif not node_text_equality(existing, node):
            if existing:
                logger.warning(
                    'Adding a node that already exists: %s', node.label_id())

            if ((node.node_type == Node.APPENDIX and len(node.label) == 2) or
                    node.node_type == Node.SUBPART):
                return self.add_to_root(node)
            else:
                if parent_label:
                    parent = self.find_node(parent_label)
                else:
                    parent = self.get_parent(node)

                if parent is None:
                    # This is a corner case, where we're trying to add a child
                    # to a parent that should exist.
                    logger.warning('No existing parent for: %s',
                                   node.label_id())
                    parent = self.create_empty_node(get_parent_label(node))
                # Fix the case where the node with label "<PART>-Subpart" is
                # the correct parent.
                if (parent.children and
                        parent.children[0].node_type == Node.EMPTYPART):
                    parent = parent.children[0]
                parent.children = self.add_child(
                    parent.children, node,
                    getattr(parent, 'child_labels', []))

    def insert_in_order(self, node):
        """Add a new node, but determine its position in its parent by looking
        at the siblings' texts"""
        parent = self.get_parent(node)
        texts = [child.text for child in parent.children]
        insert_idx = bisect(texts, node.text)
        parent.children.insert(insert_idx, node)

    def replace_node_text(self, label, change):
        """ Replace just a node's text. """

        node = find(self.tree, label)
        node.text = change['node']['text']

    def replace_node_title(self, label, change):
        """ Replace just a node's title. """

        node = find(self.tree, label)
        node.title = change['node']['title']

    def replace_node_heading(self, label, change):
        """ A node's heading is it's keyterm. We handle this here, but not
        well, I think. """
        node = find(self.tree, label)
        node.text = replace_first_sentence(node.text, change['node']['text'])

        if node.tagged_text and 'tagged_text' in change['node']:
            node.tagged_text = replace_first_sentence(
                node.tagged_text, change['node']['tagged_text'])

    def create_new_subpart(self, subpart_label):
        """ Create a whole new subpart. """

        # XXX Subparts need titles. We'll need to pull this up from parsing.
        subpart_node = Node('', [], subpart_label, None, Node.SUBPART)
        self.add_to_root(subpart_node)
        return subpart_node

    def move_to_subpart(self, label, subpart_label):
        """ Move an existing node to another subpart. If the new subpart
        doesn't exist, create it. """
        if len(label.split('-')) != 2:
            logger.error(
                "Trying to move a non-section into a subpart: %s -> %s",
                label, subpart_label)
            return

        destination = find(self.tree, '-'.join(subpart_label))

        if destination is None:
            destination = self.create_new_subpart(subpart_label)

        subpart_with_node = find_parent(self.tree, label)

        if destination and subpart_with_node:
            node = find(subpart_with_node, label)
            other_children = [c for c in subpart_with_node.children
                              if c.label_id() != label]
            subpart_with_node.children = other_children
            destination.children = self.add_child(destination.children, node)

            if not subpart_with_node.children:
                self.delete('-'.join(subpart_with_node.label))


def dict_to_node(node_dict):
    """ Convert a dictionary representation of a node into a Node object if
    it contains the minimum required fields. Otherwise, pass it through
    unchanged. """
    minimum_fields = set(('text', 'label', 'node_type'))
    if minimum_fields.issubset(node_dict.keys()):
        node = Node(
            node_dict['text'], [], node_dict['label'],
            node_dict.get('title', None), node_dict['node_type'])
        if 'tagged_text' in node_dict:
            node.tagged_text = node_dict['tagged_text']
        if 'child_labels' in node_dict:
            node.child_labels = node_dict['child_labels']
        return node
    else:
        return node_dict


def sort_labels(labels):
    """ Deal with higher up elements first. """
    sorted_labels = sorted(labels, key=len)

    # The length of a Subpart label doesn't indicate it's level in the tree
    subparts = [l for l in sorted_labels if 'Subpart' in l]
    non_subparts = [l for l in sorted_labels if 'Subpart' not in l]

    return subparts + non_subparts


def replace_node_field(reg, label, change):
    """ Call one of the field appropriate methods if we're changing just
    a field on a node. """

    if change['action'] == 'PUT' and change['field'] == '[text]':
        reg.replace_node_text(label, change)
    elif change['action'] == 'PUT' and change['field'] == '[title]':
        reg.replace_node_title(label, change)
    elif change['action'] == 'PUT' and change['field'] == '[heading]':
        reg.replace_node_heading(label, change)


def one_change(reg, label, change):
    """Notices are generally composed of many changes; this method handles a
    single change to the tree."""
    field_list = ['[text]', '[title]', '[heading]']
    replace_subtree = 'field' not in change

    if change['action'] == 'PUT' and replace_subtree:
        node = dict_to_node(change['node'])
        reg.replace_node_and_subtree(node)
    elif change['action'] == 'PUT' and change['field'] in field_list:
        replace_node_field(reg, label, change)
    elif change['action'] == 'POST':
        node = dict_to_node(change['node'])
        reg.add_node(node, change.get('parent_label'))
    elif change['action'] == 'DESIGNATE':
        if 'Subpart' in change['destination']:
            reg.move_to_subpart(label, change['destination'])
    elif change['action'] == 'MOVE':
        reg.move(label, change['destination'])
    elif change['action'] == 'DELETE':
        reg.delete(label)
    elif change['action'] == 'RESERVE':
        node = dict_to_node(change['node'])
        reg.reserve(label, node)
    elif change['action'] == 'INSERT':
        node = dict_to_node(change['node'])
        reg.insert_in_order(node)
    else:
        logger.warning("Unsure how to compile with this action: %s @ %s",
                       change['action'], label)


def _needs_delay(reg, change):
    """Determine whether we should delay processing this change. This will
    be used in a second pass when compiling the reg"""
    action = change['action']

    if action == 'MOVE':
        return reg.contains(change['destination'])
    if action == 'POST':
        existing = reg.find_node(change['node']['label'])
        return existing and not is_reserved_node(existing)
    return False


def compile_regulation(previous_tree, notice_changes):
    """ Given a last full regulation tree, and the set of changes from the
    next final notice, construct the next full regulation tree. """
    reg = RegulationTree(previous_tree)
    labels = sort_labels(notice_changes.keys())

    reg_part = previous_tree.label[0]
    labels = filter(lambda l: l.split('-')[0] == reg_part, labels)

    next_pass = [(label, change)
                 for label in labels
                 for change in notice_changes[label]]
    pass_len = len(next_pass) + 1

    reg.keep(l for l, change in next_pass if change['action'] == Verb.KEEP)
    next_pass = [pair for pair in next_pass if pair[1]['action'] != Verb.KEEP]

    #   Monotonically decreasing length - guarantees we'll end
    while pass_len > len(next_pass):
        pass_len = len(next_pass)
        current_pass, next_pass = next_pass, []
        for label, change in current_pass:
            if _needs_delay(reg, change):
                next_pass.append((label, change))
            else:
                one_change(reg, label, change)

    # Force any remaining changes -- generally means something went wrong
    for label, change in next_pass:
        logger.warning('Conflicting Change: %s:%s', label, change['action'])
        one_change(reg, label, change)
    return reg.tree
