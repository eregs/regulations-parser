from copy import deepcopy
from functools import partial

from lxml import etree


class XMLBuilder(object):
    """A small DSL for generating XML. For example,
        with XMLBuilder("ROOT") as ctx:
            ctx.P("Some Text")
            with ctx.SECT(level=4):
                ctx.P("More")

        ctx.xml_str:
        <ROOT>
            <P>Some Text</P>
            <SECT level="4">
                <P>More</P>
            </SECT>
        </ROOT>"""
    def __init__(self, *args, **kwargs):
        self.cursor = etree.Element('SUPER_ROOT')
        args = args or ['ROOT']
        self.child(*args, **kwargs)

    def child(self, tag, _text=None, **kwargs):
        """Add a child to our xml."""
        el = etree.Element(tag)
        for key, value in sorted(kwargs.items()):
            el.set(key, str(value))
        el.text = _text
        self.cursor.append(el)
        return self

    def child_from_string(self, xml_str):
        """It can be easier to describe a child via straight XML"""
        self.cursor.append(etree.fromstring(xml_str))
        return self

    def __getattr__(self, name):
        """Handle unknown attributes by calling `self.child`"""
        return partial(self.child, name)

    def __enter__(self):
        """Focus on the most recently added child"""
        self.cursor = self.cursor[-1]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove focus"""
        self.cursor = self.cursor.getparent()
        return False

    @property
    def xml(self):
        return self.cursor[-1]

    @property
    def xml_str(self):
        return etree.tounicode(self.xml)

    def xml_copy(self):
        return deepcopy(self.xml)
