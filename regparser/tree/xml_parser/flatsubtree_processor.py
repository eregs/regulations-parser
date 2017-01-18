from regparser.tree.depth import markers as mtypes
from regparser.tree.struct import Node
from regparser.tree.xml_parser import (paragraph_processor,
                                       simple_hierarchy_processor, us_code)


class FlatParagraphProcessor(paragraph_processor.ParagraphProcessor):
    """Paragraph Processor which does not try to derive paragraph markers"""
    MATCHERS = [paragraph_processor.StarsMatcher(),
                paragraph_processor.TableMatcher(),
                simple_hierarchy_processor.SimpleHierarchyMatcher(
                    ['NOTE', 'NOTES'], Node.NOTE),
                paragraph_processor.HeaderMatcher(),
                paragraph_processor.SimpleTagMatcher('P', 'FP'),
                us_code.USCodeMatcher(),
                paragraph_processor.GraphicsMatcher(),
                paragraph_processor.IgnoreTagMatcher('PRTPAGE')]


class FlatsubtreeMatcher(paragraph_processor.BaseMatcher):
    """
    Detects tags passed to it on init and processes them with the
    FlatParagraphProcessor. Also optionally sets node_type.
    """
    def __init__(self, tags, node_type=Node.REGTEXT):
        self.tags = list(tags)
        self.node_type = node_type

    def matches(self, xml):
        return xml.tag in self.tags

    def derive_nodes(self, xml, processor=None):
        processor = FlatParagraphProcessor()
        text = (xml.text or '').strip()
        node = Node(text=text, node_type=self.node_type,
                    label=[mtypes.MARKERLESS])
        return [processor.process(xml, node)]
