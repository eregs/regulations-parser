import difflib
import re

from regparser.diff.text import DELETE, EQUAL, INSERT, REPLACE, get_opcodes
from regparser.tree import struct

ADDED = 'added'
MODIFIED = 'modified'
DELETED = 'deleted'

_whitespace = re.compile(u'\\s', re.UNICODE)    # aware of "thin" spaces, etc.


def _local_text_changes(lhs, rhs):
    """Account for only text changes between nodes. This explicitly excludes
    children"""
    l_text, r_text, l_title, r_title = [
        _whitespace.sub(' ', text)
        for text in (lhs.text, rhs.text, lhs.title, rhs.title)]
    if l_text != r_text or l_title != r_title:
        node_changes = {"op": MODIFIED}

        text_opcodes = get_opcodes(l_text, r_text)
        if text_opcodes:
            node_changes["text"] = text_opcodes

        title_opcodes = get_opcodes(l_title, r_title)
        if title_opcodes:
            node_changes["title"] = title_opcodes
        return (lhs.label_id, node_changes)


def label_opcodes(lhs, rhs):
    """Determine the differences between two lists of labels, encoded as a
    generator of opcodes. The result will not include REPLACE (instead,
    deleting and inserting) and when inserting, it'll include the labels which
    have been added"""
    seqm = difflib.SequenceMatcher(a=lhs, b=rhs)
    for op, l_start, l_end, r_start, r_end in seqm.get_opcodes():
        if op == INSERT:
            yield (op, l_start, rhs[r_start:r_end])
        elif op == REPLACE:
            yield (DELETE, l_start, l_end)
            yield (INSERT, l_start, rhs[r_start:r_end])
        elif op in (DELETE, EQUAL):     # this should be all cases
            yield (op, l_start, l_end)


def _local_changes(lhs, rhs):
    """Include changes to text, title, or children"""
    changes = _local_text_changes(lhs, rhs)
    if lhs.child_labels != rhs.child_labels:
        if not changes:
            changes = (lhs.label_id, {'op': MODIFIED})
        changes[1]['child_ops'] = list(label_opcodes(lhs.child_labels,
                                                     rhs.child_labels))
    return [changes] if changes else []


def _new_in_rhs(lhs_list, rhs_list):
    """Compare the lhs and rhs lists to see if the rhs contains elements not
    in the lhs"""
    added = []
    lhs_codes = tuple(n.label_id for n in lhs_list)
    for node in rhs_list:
        if node.label_id not in lhs_codes:
            added.append(node)
    return added


def _data_for_add(node):
    node_as_dict = {
        'child_labels': node.child_labels,
        'label': node.label,
        'node_type': node.node_type,
        'tagged_text': node.tagged_text or None,  # maintain backwards compat
        'text': node.text,
        'title': node.title or None,
    }
    return (node.label_id, {"op": ADDED, "node": node_as_dict})


def _data_for_delete(node):
    return (node.label_id, {"op": DELETED})


def changes_between(lhs, rhs):
    """Main entry point for this library. Recursively return a list of changes
    between the lhs and rhs. lhs and rhs should be FrozenNodes. This also
    accounts for reordering nodes, including moves due to subpart renames."""
    changes = []
    if lhs == rhs:
        return changes

    changes.extend(_local_changes(lhs, rhs))

    # Removed children. Note params reversed
    removed_children = _new_in_rhs(rhs.children, lhs.children)
    changes.extend(_data_for_delete(c) for c in removed_children)
    # grandchildren which appear to be deleted, but may just have been moved
    possibly_moved = {}
    for child in removed_children:
        for grandchild in child.children:
            possibly_moved[grandchild.label_id] = grandchild

    # New children. Determine if they are added or moved
    for added in _new_in_rhs(lhs.children, rhs.children):
        changes.append(_data_for_add(added))
        for grandchild in added.children:
            if grandchild.label_id in possibly_moved:   # it *was* moved
                changes.extend(changes_between(
                    possibly_moved[grandchild.label_id], grandchild))
                del possibly_moved[grandchild.label_id]
            else:   # Not moved; recursively add all of it's children
                changes.extend(struct.walk(grandchild, _data_for_add))

    # Remaining nodes weren't moved; they were *re*moved
    for removed in possibly_moved.values():
        changes.extend(struct.walk(removed, _data_for_delete))

    # Recurse on modified children. Again, this does *not* track reordering
    for lhs_child in lhs.children:
        for rhs_child in rhs.children:
            if lhs_child.label_id == rhs_child.label_id:
                changes.extend(changes_between(lhs_child, rhs_child))
    return changes
