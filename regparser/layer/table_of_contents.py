# -*- coding: utf-8 -*-
from regparser.layer.layer import Layer
from regparser.tree.struct import Node


class TableOfContentsLayer(Layer):
    shorthand = 'toc'

    @staticmethod
    def _relevant_nodes(node):
        """Empty parts are not displayed, so we'll skip them to find their
        children"""
        if node.node_type == Node.EMPTYPART:
            for child in node.children:
                yield child
        else:
            yield node

    def check_toc_candidacy(self, node):
        """ To be eligible to contain a table of contents, all of a node's
        children must have a title element. If one of the children is an
        empty subpart, we check all it's children.  """

        return all(relevant.title
                   for child in node.children
                   for relevant in self._relevant_nodes(child))

    def process(self, node):
        """ Create a table of contents for this node, if it's eligible. We
        ignore subparts. """

        if self.check_toc_candidacy(node):
            return [{'index': relevant.label, 'title': relevant.title}
                    for child in node.children
                    for relevant in self._relevant_nodes(child)]
        return None
