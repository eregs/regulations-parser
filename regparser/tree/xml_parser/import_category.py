"""Example processor for the IMPORTCATEGORY tag. This will be replaced with
something more sophisticated and should be in an ATF-specific submodule"""
from regparser.tree.struct import Node
from regparser.tree.xml_parser import flatsubtree_processor


class ImportCategoryMatcher(flatsubtree_processor.FlatsubtreeMatcher):
    def __init__(self):
        super(ImportCategoryMatcher, self).__init__(tags=['IMPORTCATEGORY'],
                                                    node_type=Node.EXTRACT)
