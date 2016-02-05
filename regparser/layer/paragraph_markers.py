import string

import pyparsing

from regparser.grammar import atomic
from regparser.grammar.utils import QuickSearchable
from regparser.layer.layer import Layer


_parens = (atomic.lower_p | atomic.digit_p | atomic.roman_p | atomic.upper_p)
_parens_through = _parens + "-" + _parens
_periods = (
    (pyparsing.Word(string.digits) | pyparsing.Word(string.ascii_letters)) +
    pyparsing.Literal(".").leaveWhitespace())
_periods_through = _periods + "-" + _periods
all_markers = QuickSearchable(
    # Use "^" so we collect the longest match
    _parens ^ _parens_through ^ _periods ^ _periods_through)


def marker_of(node):
    """Try multiple potential marker formats. See if any apply to this
    node."""
    text = node.text.strip()
    for _, start, end in all_markers.scanString(text):
        if start == 0:
            return text[:end]
    return ''


class ParagraphMarkers(Layer):
    def process(self, node):
        """Look for any leading paragraph markers."""
        marker = marker_of(node)
        if marker:
            return [{"text": marker, "locations": [0]}]
