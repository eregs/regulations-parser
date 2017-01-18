from copy import deepcopy

import six
from lxml import etree

from regparser import plugins
from regparser.tree.xml_parser.preprocessors import replace_html_entities


class XMLWrapper(object):
    """Wrapper around XML which provides a consistent interface shared by both
    Notices and Annual editions of XML"""
    def __init__(self, xml, source=None):
        """Includes automatic conversion from string and a deep copy for
        safety. `source` represents the providence of this xml. It is _not_
        serialized and hence does not follow the xml through the index"""
        if isinstance(xml, six.binary_type):
            xml = replace_html_entities(xml)
            self.xml = etree.fromstring(xml)
        elif isinstance(xml, etree._Element):
            self.xml = deepcopy(xml)
        else:
            raise ValueError("xml should be either binary or an lxml node")
        self.source = source

    def preprocess(self):
        """Unfortunately, the notice xml is often inaccurate. This function
        attempts to fix some of those (general) flaws. For specific issues, we
        tend to instead use the files in settings.LOCAL_XML_PATHS"""

        for plugin in plugins.instantiate_if_possible(
                'eregs_ns.parser.preprocessors', method_name='transform'):
            plugin(self.xml)

        return self

    def xpath(self, *args, **kwargs):
        return self.xml.xpath(*args, **kwargs)

    def xml_str(self):
        return etree.tounicode(self.xml, pretty_print=True)

    def _find_or_create(self, tag):
        """Look for the first matching tag present in the document. If it's
        not present, create it by inserting it into the root"""
        matches = self.xpath('//' + tag)
        if matches:
            return matches[0]
        else:
            return etree.SubElement(self.xml, tag)
