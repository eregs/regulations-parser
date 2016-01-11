from layer import Layer
from regparser.tree.struct import Node


def marker_of(node):
    """Try multiple potential marker formats. See if any apply to this node."""
    marker = [l for l in node.label if l != Node.INTERP_MARK][-1]
    for fmt in ('{}.', '({})'):
        potential_marker = fmt.format(marker)
        if node.text.strip().startswith(potential_marker):
            return potential_marker


class ParagraphMarkers(Layer):
    def process(self, node):
        """Look for any leading paragraph markers. Try multiple potential
        marker formats"""
        marker = marker_of(node)
        if marker:
            return [{'text': marker, 'locations': [0]}]
