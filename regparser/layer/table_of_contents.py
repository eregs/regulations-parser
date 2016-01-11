# vim: set encoding=utf-8
from layer import Layer
from regparser.tree.struct import Node, node_type_cases


class TableOfContentsLayer(Layer):
    @staticmethod
    def _titles(node):
        """Empty parts are not displayed, so we'll skip them to find the
        titles of their children"""
        with node_type_cases(node.node_type) as case:
            if case.match(Node.EMPTYPART):
                for child in node.children:
                    yield child.title
            if case.match(Node.APPENDIX, Node.INTERP, Node.REGTEXT,
                          Node.SUBPART, Node.EXTRACT):
                yield node.title

    def check_toc_candidacy(self, node):
        """ To be eligible to contain a table of contents, all of a node's
        children must have a title element. If one of the children is an
        empty subpart, we check all it's children.  """

        return any(not child_title
                   for child in node.children
                   for child_title in self._titles(child))

    def process(self, node):
        """ Create a table of contents for this node, if it's eligible. We
        ignore subparts. """

        if self.check_toc_candidacy(node):
            layer_element = []
            for child in node.children:
                with node_type_cases(child) as case:
                    if case.match(Node.EMPTYPART):
                        layer_element.extend(
                            {'index': sub.label, 'title': sub.title}
                            for sub in child.children)
                    if case.match(Node.APPENDIX, Node.INTERP, Node.REGTEXT,
                                  Node.SUBPART, Node.EXTRACT):
                        layer_element.append(
                            {'index': child.label, 'title': child.title})
            return layer_element
        return None
