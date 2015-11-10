from regparser.tree.depth import markers as mtypes
from regparser.tree.struct import Node
from regparser.tree.xml_parser import paragraph_processor


class ExtractParagraphProcessor(paragraph_processor.ParagraphProcessor):
    """Paragraph Processor which does not try to derive paragraph markers"""
    MATCHERS = [paragraph_processor.StarsMatcher(),
                paragraph_processor.TableMatcher(),
                paragraph_processor.FencedMatcher(),
                paragraph_processor.HeaderMatcher(),
                paragraph_processor.SimpleTagMatcher('P', 'FP')]


class ExtractMatcher(object):
    def matches(self, xml):
        return xml.tag in ('EXTRACT',)

    def derive_nodes(self, xml, processor=None):
        extract_node = Node(text=(xml.text or '').strip(),
                            node_type=u"extract", label=[mtypes.MARKERLESS])
        return [ExtractParagraphProcessor().process(xml, extract_node)]
