import abc
import logging
from collections import OrderedDict

import six
from lxml import etree

from regparser.layer.formatting import table_xml_to_plaintext
from regparser.layer.key_terms import KeyTerms
from regparser.tree.depth import markers as mtypes
from regparser.tree.depth import heuristics
from regparser.tree.depth.derive import debug_idx, derive_depths
from regparser.tree.depth.markers import deemphasize
from regparser.tree.paragraph import hash_for_paragraph
from regparser.tree.struct import Node
from regparser.tree.xml_parser import tree_utils

logger = logging.getLogger(__name__)


class ParagraphProcessor(object):
    """Processing paragraphs in a generic manner requires a lot of state to be
    carried in between xml nodes. Use a class to wrap that state so we can
    compartmentalize processing with various tags. This is an abstract class;
    regtext, interpretations, appendices, etc. should inherit and override
    where needed"""

    # Subclasses should override the following interface
    MATCHERS = []

    # Subclasses may choose to change the depth-deriving heuristics or weights
    DEPTH_HEURISTICS = OrderedDict()
    DEPTH_HEURISTICS[heuristics.prefer_diff_types_diff_levels] = 0.8
    DEPTH_HEURISTICS[heuristics.prefer_multiple_children] = 0.4
    DEPTH_HEURISTICS[heuristics.prefer_shallow_depths] = 0.2
    DEPTH_HEURISTICS[heuristics.prefer_no_markerless_sandwich] = 0.2

    def parse_nodes(self, xml):
        """Derive a flat list of nodes from this xml chunk. This does nothing
        to determine node depth"""
        nodes = []

        for child in xml.getchildren():
            matching = (m for m in self.MATCHERS if m.matches(child))

            tag_matcher = next(matching, None)
            if tag_matcher:
                nodes.extend(tag_matcher.derive_nodes(child, processor=self))
            else:
                logger.warning("No tag match\n%s", etree.tounicode(child))

        # Trailing stars don't matter; slightly more efficient to ignore them
        while nodes and nodes[-1].label[0] in mtypes.stars:
            nodes = nodes[:-1]

        return nodes

    def select_depth(self, depths):
        """There might be multiple solutions to our depth processing problem.
        Use heuristics to select one."""
        for fn, weight in self.DEPTH_HEURISTICS.items():
            depths = fn(depths, weight)
        depths = sorted(depths, key=lambda d: d.weight, reverse=True)
        return depths[0]

    def build_hierarchy(self, root, nodes, depths):
        """Given a root node, a flat list of child nodes, and a list of
        depths, build a node hierarchy around the root"""
        stack = tree_utils.NodeStack()
        stack.add(0, root)
        for node, depth_info in zip(nodes, depths):
            node.label = [mtypes.deemphasize(l) for l in node.label]
            self.replace_markerless(stack, node, depth_info.depth + 1)
            self.carry_label_to_children(node)
            if depth_info.typ != mtypes.stars:
                stack.add(1 + depth_info.depth, node)
        return stack.collapse()

    def carry_label_to_children(self, node):
        """Takes a node and recursively processes its children to add the
        appropriate label prefix to them."""
        for child in node.children:
            child.label = node.label + child.label[-1:]
            self.carry_label_to_children(child)

    @staticmethod
    def replace_markerless(stack, node, depth):
        """Assign a unique index to all of the MARKERLESS paragraphs"""
        if node.label[-1] == mtypes.MARKERLESS:
            keyterm = KeyTerms.keyterm_in_node(node, ignore_definitions=False)
            if keyterm:
                p_num = hash_for_paragraph(keyterm)
            else:
                # len(n.label[-1]) < 6 filters out keyterm nodes
                p_num = sum(n.is_markerless() and len(n.label[-1]) < 6
                            for n in stack.peek_level(depth)) + 1
            node.label[-1] = 'p{0}'.format(p_num)

    @staticmethod
    def separate_intro(nodes):
        """In many situations the first unlabeled paragraph is the "intro"
        text for a section. We separate that out here"""
        labels = [n.label[0] for n in nodes]    # label is only one part long

        only_one = labels == [mtypes.MARKERLESS]
        switches_after_first = (
            len(nodes) > 1 and
            labels[0] == mtypes.MARKERLESS and
            labels[1] != mtypes.MARKERLESS)

        first_xml = nodes[0].source_xml if len(nodes) else None
        table_first = first_xml is not None and first_xml.tag == "GPOTABLE"
        extract_first = nodes[0].node_type == "extract" if len(nodes) else None
        has_title = nodes[0].title if len(nodes) else None
        if not any([table_first, extract_first, has_title]) and any(
                [only_one, switches_after_first]):
            return nodes[0], nodes[1:]
        else:
            return None, nodes

    def process(self, xml, root):
        nodes = self.parse_nodes(xml)
        intro_node, nodes = self.separate_intro(nodes)
        if intro_node:
            root.text = " ".join([root.text, intro_node.text]).strip()
            tagged_text_list = []
            if root.tagged_text:
                tagged_text_list.append(root.tagged_text)
            if intro_node.tagged_text:
                tagged_text_list.append(intro_node.tagged_text)
            if tagged_text_list:
                root.tagged_text = ' '.join(tagged_text_list)
        if nodes:
            markers = [node.label[0] for node in nodes]
            constraints = self.additional_constraints()
            depths = derive_depths(markers, constraints)

            if not depths:
                logger.warning("Could not derive paragraph depths."
                               " Retrying with relaxed constraints.")
                deemphasized_markers = [deemphasize(m) for m in markers]
                constraints = self.relaxed_constraints()
                depths = derive_depths(deemphasized_markers, constraints)

            if not depths:
                fails_at = debug_idx(markers, constraints)
                logger.error(
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

    @staticmethod
    def additional_constraints():
        """Hook for subtypes to add additional constraints"""
        return []

    @staticmethod
    def relaxed_constraints():
        """Hook for subtypes to add relaxed constraints for retry
           logic"""
        return []


class BaseMatcher(six.with_metaclass(abc.ABCMeta)):
    """Base class defining the interface of various XML node matchers"""
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
        tagged = tree_utils.get_node_text_tags_preserved(xml).strip()
        return [Node(text=tree_utils.get_node_text(xml).strip(),
                     tagged_text=tagged,
                     label=[mtypes.MARKERLESS])]


class IgnoreTagMatcher(SimpleTagMatcher):
    """As we log warnings when we don't know how to process a tag, this
    matcher allows us to positively acknowledge that we're ignoring some
    matches"""
    def derive_nodes(self, xml, processor=None):
        return []


class TableMatcher(BaseMatcher):
    """Matches the GPOTABLE tag"""
    def matches(self, xml):
        return xml.tag == 'GPOTABLE'

    def derive_nodes(self, xml, processor=None):
        node = Node(table_xml_to_plaintext(xml), label=[mtypes.MARKERLESS],
                    source_xml=xml)
        node.tagged_text = etree.tounicode(xml).strip()
        return [node]


class HeaderMatcher(BaseMatcher):
    def matches(self, xml):
        return xml.tag == "HD"

    def derive_nodes(self, xml, processor=None):
        # This should match HD elements only at lower levels, and for now we'll
        # just put them into the titles
        return [Node(text='', title=tree_utils.get_node_text(xml).strip(),
                     label=[mtypes.MARKERLESS])]


class FencedMatcher(BaseMatcher):
    """Use github-like fencing to indicate this is code"""
    def matches(self, xml):
        return xml.tag == 'CODE'

    def derive_nodes(self, xml, processor=None):
        texts = ["```" + xml.get('LANGUAGE', 'code')]
        for child in xml:
            text = tree_utils.get_node_text(child).strip()
            if text:
                texts.append(text)
        texts.append("```")

        return [Node("\n".join(texts), label=[mtypes.MARKERLESS])]


class GraphicsMatcher(BaseMatcher):
    """Convert Graphics tags into a markdown-esque format"""
    def matches(self, xml):
        return xml.tag == 'GPH'

    def derive_nodes(self, xml, processor=None):
        text = ''
        for gid_xml in xml.xpath('./GID'):
            text += '![]({0})'.format(gid_xml.text)
        return [Node(text, label=[mtypes.MARKERLESS])]
