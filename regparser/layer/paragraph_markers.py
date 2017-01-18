import re

from regparser.layer.layer import Layer
from regparser.tree.struct import Node

_marker_re = r'([0-9]+|[a-z]+|[A-Z]+)'


def marker_of(node):
    """Try multiple potential marker formats. See if any apply to this
    node."""
    text = node.text.strip()
    relevant = [l for l in node.label if l != Node.INTERP_MARK]
    if not relevant:
        return ''
    elif text.startswith('('):
        regex_fmt = r'\({0}\)'
    else:
        regex_fmt = r'{0}\.'
    # Begin with the appropriate marker, potentially followed by a dash and
    # another marker, ignoring whitespace
    regex = r'{0}(\s*-\s*{1})?'.format(regex_fmt.format(relevant[-1]),
                                       regex_fmt.format(_marker_re))
    match = re.match(regex, text)
    if match:
        return text[:match.end()]
    else:
        return ''


class ParagraphMarkers(Layer):
    shorthand = 'paragraph-markers'

    def process(self, node):
        """Look for any leading paragraph markers."""
        marker = marker_of(node)
        if marker:
            return [{"text": marker, "locations": [0]}]
