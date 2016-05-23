from copy import deepcopy

from lxml import etree
import six

from regparser.plugins import class_paths_to_classes
import settings


class XMLWrapper(object):
    """Wrapper around XML which provides a consistent interface shared by both
    Notices and Annual editions of XML"""
    def __init__(self, xml, source=None):
        """Includes automatic conversion from string and a deep copy for
        safety. `source` represents the providence of this xml. It is _not_
        serialized and hence does not follow the xml through the index"""
        if isinstance(xml, six.string_types):
            self.xml = etree.fromstring(xml)
        else:
            self.xml = deepcopy(xml)
        self.source = source

    @property
    def source_is_local(self):
        """Determine whether or not `self.source` refers to a local file"""
        protocol = (self.source or '').split('://')[0]
        return protocol not in ('http', 'https')

    def preprocess(self):
        """Unfortunately, the notice xml is often inaccurate. This function
        attempts to fix some of those (general) flaws. For specific issues, we
        tend to instead use the files in settings.LOCAL_XML_PATHS"""

        for preprocessor in class_paths_to_classes(settings.PREPROCESSORS):
            preprocessor().transform(self.xml)

        return self

    def xpath(self, *args, **kwargs):
        return self.xml.xpath(*args, **kwargs)

    def xml_str(self):
        return etree.tostring(self.xml, pretty_print=True)
