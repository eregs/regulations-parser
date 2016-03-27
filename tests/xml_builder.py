from contextlib import contextmanager

from lxml import etree

from regparser.test_utils.xml_builder import XMLBuilder


class LXMLBuilder(object):
    """Wrapper around a datatree which provides `render` methods and removes a
    bit of the redundancy found in tests. See
    tests/tree_xml_parser_reg_text_tests.py for example usage"""

    def builder(self, root_tag, **kwargs):
        """Create a datatree with the root_tag at the root"""
        tree = XMLBuilder(root_tag, **kwargs)
        self.root = tree
        return tree

    def render_xml(self):
        return self.root.xml

    def render_string(self):
        return self.root.xml_str


class XMLBuilderMixin(object):
    """Mix in to tests to provide access to a builder via self.tree"""
    def setUp(self):
        super(XMLBuilderMixin, self).setUp()
        self.tree = LXMLBuilder()

    def empty_xml(self):
        builder = LXMLBuilder()
        with builder.builder('ROOT'):
            pass
        return builder.render_xml()

    @contextmanager
    def assert_xml_transformed(self):
        """This verifies that XML has been transformed the way we expect.
        Usage:

        with self.assert_xml_transformed() as original_xml:
            some_transform(xml)
            with self.tree.builder("TAG1") as tag1:
                ...

        in which case, the mutated xml is tested against the final value of
        self.tree
        """
        xml = self.tree.render_xml()
        yield xml
        new_xml = self.tree.render_xml()
        self.assertEqual(etree.tostring(xml), etree.tostring(new_xml))
