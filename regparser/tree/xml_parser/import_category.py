import logging
import re
from copy import deepcopy

from regparser.tree.depth import markers as mtypes
from regparser.tree.paragraph import hash_for_paragraph
from regparser.tree.struct import Node
from regparser.tree.xml_parser import paragraph_processor, tree_utils


class ImportCategoryMatcher(paragraph_processor.BaseMatcher):
    """The IMPORTCATEGORY gets converted into a subtree with an appropriate
    title and unique paragraph marker"""
    CATEGORY_RE = re.compile(r'categor(y|ies) (?P<category>[ivx]+).*',
                             re.IGNORECASE)

    def matches(self, xml):
        return xml.tag == 'IMPORTCATEGORY'

    def derive_nodes(self, xml, processor=None):
        """Finds and deletes the category header before recursing. Adds this
        header as a title."""
        xml = deepcopy(xml)     # we'll be modifying this
        header = xml.xpath('./HD')[0]
        xml.remove(header)
        header_text = tree_utils.get_node_text(header)

        node = Node(title=header_text, label=[self.marker(header_text)])
        return [processor.process(xml, node)]

    @classmethod
    def marker(cls, header_text):
        """Derive a unique, repeatable identifier for this subtree. This
        allows the same category to be reordered (e.g. if a note has been
        added), or a header with multiple reserved categories to be split
        (which would also re-order the categories that followed)"""
        match = cls.CATEGORY_RE.match(header_text)
        if match:
            return 'p{0}'.format(hash_for_paragraph(match.group('category')))
        else:
            logging.warning("Couldn't derive category: %s", header_text)
            return mtypes.MARKERLESS
