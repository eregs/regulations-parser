import re

from regparser.layer.layer import Layer

_MARKER_RE = re.compile(r'^([0-9]+|[a-z]+|[A-Z]+)\.')


def marker_of(node):
    """Analog of regparser.layer.paragraph_markers.marker_of, but a bit more
    forgiving as it does not require the node have a corresponding label"""
    match = _MARKER_RE.match(node.text.strip())
    if match:
        return match.group(0)
    else:
        return ''


class ParagraphMarkers(Layer):
    shorthand = 'paragraph-markers'

    def process(self, node):
        """Look for any leading paragraph markers"""
        marker = marker_of(node)
        if marker:
            return [{"text": marker, "locations": [0]}]
