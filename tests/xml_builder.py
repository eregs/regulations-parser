from contextlib import contextmanager

import datatree
from datatree.render.base import Renderer
from lxml import etree


class LXMLBuilder(object):
    """Wrapper around a datatree which provides `render` methods and removes a
    bit of the redundancy found in tests. See
    tests/tree_xml_parser_reg_text_tests.py for example usage"""

    @contextmanager
    def builder(self, root_tag, **kwargs):
        """Create a datatree with the root_tag at the root"""
        tree = datatree.Tree()
        tree.register_renderer(LXMLRenderer)
        with getattr(tree, root_tag)(**kwargs) as root:
            yield root
            self.root = root

    def render_xml(self):
        return self.root.render('lxml', as_root=True)

    def render_string(self):
        return etree.tostring(self.render_xml())


class LXMLRenderer(Renderer):
    """Outputs lxml tree nodes. Based on the etree renderer"""
    friendly_names = ['lxml']

    def render_verbatim(self, node):
        """It's sometimes easier to describe the node with raw XML"""
        element = etree.fromstring(u'<{0}>{1}</{0}>'.format(
            node.__node_name__, node.__attrs__['_xml']))

        for key, value in node.__attrs__.iteritems():
            if key != '_xml':
                element.attrib[key] = str(value)

        return element

    def render_attributes(self, node):
        """Normal path: attributes are described via __attrs__"""
        attrs = {}
        for key, value in node.__attrs__.iteritems():
            attrs[key] = str(value)
        element = etree.Element(node.__node_name__, attrs)
        element.text = node.__value__ or ""
        return element

    def render_node(self, node, parent=None, options={}):
        """Generate the current node, potentially adding it to a parent, then
        recurse on children"""
        if '_xml' in node.__attrs__:
            element = self.render_verbatim(node)
        else:
            element = self.render_attributes(node)

        if parent is not None:
            parent.append(element)

        for child in node.__children__:
            self.render_node(child, element)

        return element

    def render_final(self, rendered, options={}):
        """Part of the Renderer interface"""
        return rendered


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
