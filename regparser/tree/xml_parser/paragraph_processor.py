import abc
import logging

from regparser.layer.formatting import table_xml_to_plaintext
from regparser.tree.depth import heuristics, markers as mtypes
from regparser.tree.depth.derive import debug_idx, derive_depths
from regparser.tree.struct import Node
from regparser.tree.xml_parser import tree_utils


class ParagraphProcessor(object):
    """Processing paragraphs in a generic manner requires a lot of state to be
    carried in between xml nodes. Use a class to wrap that state so we can
    compartmentalize processing with various tags. This is an abstract class;
    regtext, interpretations, appendices, etc. should inherit and override
    where needed"""

    # Subclasses should override the following interface
    MATCHERS = []

    def parse_nodes(self, xml):
        """Derive a flat list of nodes from this xml chunk. This does nothing
        to determine node depth"""
        nodes = []

        for child in xml.getchildren():
            matching = (m for m in self.MATCHERS if m.matches(child))

            tag_matcher = next(matching, None)
            if tag_matcher:
                nodes.extend(tag_matcher.derive_nodes(child, processor=self))

        # Trailing stars don't matter; slightly more efficient to ignore them
        while nodes and nodes[-1].label[0] in mtypes.stars:
            nodes = nodes[:-1]

        return nodes

    def select_depth(self, depths):
        """There might be multiple solutions to our depth processing problem.
        Use heuristics to select one."""
        depths = heuristics.prefer_diff_types_diff_levels(depths, 0.8)
        depths = heuristics.prefer_multiple_children(depths, 0.4)
        depths = heuristics.prefer_shallow_depths(depths, 0.2)
        depths = sorted(depths, key=lambda d: d.weight, reverse=True)
        return depths[0]

    def build_hierarchy(self, root, nodes, depths):
        """Given a root node, a flat list of child nodes, and a list of
        depths, build a node hierarchy around the root"""
        cnt = 0   # number of nodes we've seen without a marker
        stack = tree_utils.NodeStack()
        stack.add(0, root)
        for node, par in zip(nodes, depths):
            if par.typ != mtypes.stars:
                # Note that nodes still only have the one label part
                label, cnt = self.clean_label(node.label[0], cnt)
                node.label = [label]
                # Children should also have labels applied to them:
                if len(node.children):
                    node = self.label_child_nodes(node)
                stack.add(1 + par.depth, node)

        return stack.collapse()

    def label_child_nodes(self, node):
        """
        Takes a node and recursively processes its children to add the
        appropriate labels to them.
        """
        for idx, child in enumerate(node.children):
            child.label = node.label + ["p%s" % str(idx + 1)]
            child = self.label_child_nodes(child)
        return node

    def clean_label(self, label, unlabeled_counter):
        """There are some artifacts from parsing and deriving the depth that
        we remove here"""
        if label == mtypes.MARKERLESS:
            unlabeled_counter += 1
            label = 'p{0}'.format(unlabeled_counter)

        label = label.replace('<E T="03">', '').replace('</E>', '')
        return label, unlabeled_counter

    def separate_intro(self, nodes):
        """In many situations the first unlabeled paragraph is the "intro"
        text for a section. We separate that out here"""
        labels = [n.label[0] for n in nodes]    # label is only one part long

        only_one = labels == [mtypes.MARKERLESS]
        switches_after_first = (
            len(nodes) > 1
            and labels[0] == mtypes.MARKERLESS
            and labels[1] != mtypes.MARKERLESS)

        first_xml = nodes[0].source_xml if len(nodes) else None
        table_first = first_xml is not None and first_xml.tag == "GPOTABLE"
        extract_first = nodes[0].node_type == "extract" if len(nodes) else None
        if not any(
            [table_first, extract_first]) and any(
                [only_one, switches_after_first]):
            return nodes[0], nodes[1:]
        else:
            return None, nodes

    def process(self, xml, root):
        nodes = self.parse_nodes(xml)
        intro_node, nodes = self.separate_intro(nodes)
        if intro_node:
            root.text = " ".join([root.text, intro_node.text]).strip()
            # @todo - this is ugly. Make tagged_text a legitimate field on Node
            tagged_text_list = []
            if hasattr(root, 'tagged_text'):
                tagged_text_list.append(root.tagged_text)
            if hasattr(intro_node, 'tagged_text'):
                tagged_text_list.append(intro_node.tagged_text)
            if tagged_text_list:
                root.tagged_text = ' '.join(tagged_text_list)
        if nodes:
            markers = [node.label[0] for node in nodes]
            constraints = self.additional_constraints()
            depths = derive_depths(markers, constraints)
            if not depths:
                fails_at = debug_idx(markers, constraints)
                logging.error(
                    "Could not determine paragraph depths (<%s /> %s):\n"
                    "%s\n"
                    "?? %s\n"
                    "Remaining markers: %s",
                    xml.tag, root.label_id(),
                    derive_depths(markers[:fails_at],
                                  constraints)[0].pretty_str(),
                    markers[fails_at], markers[fails_at + 1:])
            depths = self.select_depth(depths)
            return self.build_hierarchy(root, nodes, depths)
        else:
            return root

    def additional_constraints(self):
        """Hook for subtypes to add additional constraints"""
        return []


class BaseMatcher(object):
    """Base class defining the interface of various XML node matchers"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def matches(self, xml):
        """Test the xml element -- does this matcher apply?"""
        raise NotImplementedError()

    @abc.abstractmethod
    def derive_nodes(self, xml, processor=None):
        """Given an xml node which this matcher applies against, convert it
        into a list of Node structures. `processor` is the paragraph processor
        which we are being executed in. May be useful when determining how to
        create the Nodes"""
        raise NotImplementedError()


class StarsMatcher(BaseMatcher):
    """<STARS> indicates a chunk of text which is being skipped over"""
    def matches(self, xml):
        return xml.tag == 'STARS'

    def derive_nodes(self, xml, processor=None):
        return [Node(label=[mtypes.STARS_TAG])]


class SimpleTagMatcher(BaseMatcher):
    """Simple example tag matcher -- it listens for specific tags and derives
    a single node with the associated body"""
    def __init__(self, *tags):
        self.tags = list(tags)

    def matches(self, xml):
        return xml.tag in self.tags

    def derive_nodes(self, xml, processor=None):
        return [Node(text=tree_utils.get_node_text(xml).strip(),
                     label=[mtypes.MARKERLESS])]


class TableMatcher(BaseMatcher):
    """Matches the GPOTABLE tag"""
    def matches(self, xml):
        return xml.tag == 'GPOTABLE'

    def derive_nodes(self, xml, processor=None):
        return [Node(table_xml_to_plaintext(xml), label=[mtypes.MARKERLESS],
                     source_xml=xml)]


class HeaderMatcher(BaseMatcher):
    def matches(self, xml):
        return xml.tag == "HD"

    def derive_nodes(self, xml, processor=None):
        # This should match HD elements only at lower levels, and for now we'll
        # just put them into the titles
        return [Node(text='', title=tree_utils.get_node_text(xml).strip(),
                     label=[mtypes.MARKERLESS])]


class FencedMatcher(BaseMatcher):
    """Use github-like fencing to indicate this is a note/code"""
    def matches(self, xml):
        return xml.tag in ('NOTE', 'NOTES', 'CODE')

    def derive_nodes(self, xml, processor=None):
        texts = ["```" + self.fence_type(xml)]
        for child in xml:
            texts.append(tree_utils.get_node_text(child).strip())
        texts.append("```")

        return [Node("\n".join(texts), label=[mtypes.MARKERLESS])]

    def fence_type(self, xml):
        if xml.tag == 'CODE':
            return xml.get('LANGUAGE', 'code')
        else:
            return xml.tag.lower().rstrip("s")
