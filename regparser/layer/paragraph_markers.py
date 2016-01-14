from layer import Layer
from regparser.tree.struct import Node


def marker_of(node):
    """Try multiple potential marker formats. See if any apply to this
    node."""
    if node.label[-1] == Node.INTERP_MARK:
        marker = node.label[-2]
    else:
        marker = node.label[-1]

    for fmt in ('({})', '{}.'):
        potential_marker = fmt.format(marker)
        if node.text.strip().startswith(potential_marker):
            return potential_marker
    return ''


class ParagraphMarkers(Layer):
    def process(self, node):
        """Look for any leading paragraph markers."""
        marker = marker_of(node)
        if marker:
            return [{"text": marker, "locations": [0]}]
