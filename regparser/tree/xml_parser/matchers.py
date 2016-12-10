"""Utilities for converting an XML tag into a struct.Node (or set of
nodes)."""
import abc

import six


class Parser(six.with_metaclass(abc.ABCMeta, object)):
    """Describe the interface we're expecting from our tag parsers. We don't
    require the class actually be inherited from so long as the interface is
    satisfied.
    @todo - these are very similar to ParagraphProcessors; we'll want to
    combine at some point."""

    @abc.abstractmethod
    def matches(self, parent, xml_node):
        """Does this parser apply to the provides xml?"""
        raise NotImplementedError()

    @abc.abstractmethod
    def __call__(self, parent, xml_node):
        """Parse the requested xml_node, inspecting and modifying the provided
        parent"""
        raise NotImplementedError()


def match_tag(tag):
    """Decorator which marks the provided function as being applicable to the
    requested tag."""
    def process_fn(fn):
        fn.matches = lambda parent, xml_node: xml_node.tag == tag
        return fn
    return process_fn
