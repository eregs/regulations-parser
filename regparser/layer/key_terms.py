from __future__ import unicode_literals

import re

from regparser.layer.layer import Layer
from regparser.layer.paragraph_markers import marker_of
from regparser.layer.terms import Terms

KEYTERM_RE = re.compile(r'<E T="03">(?P<keyterm>[^<]*?)</E>', re.UNICODE)
TRIM_FROM_KEYTERM = ['See also', 'See']


def keyterm_in_text(tagged_text):
    """Pull out the key term of the provided markup using a regex. The XML <E>
    tags that indicate keyterms are also used for italics, which means some
    non-key term phrases would be lumped in. We eliminate them here."""
    match = KEYTERM_RE.match(tagged_text.strip())
    keyterm = ''
    if match:
        keyterm = match.group('keyterm')
    keyterm = keyterm.strip()

    for to_trim in TRIM_FROM_KEYTERM:
        if keyterm.endswith(to_trim):
            keyterm = keyterm[:-len(to_trim)].strip()

    return keyterm or None


class KeyTerms(Layer):
    shorthand = 'keyterms'

    @classmethod
    def keyterm_in_node(cls, node, ignore_definitions=True):
        tagged = node.tagged_text.replace(marker_of(node), '', 1).strip()
        keyterm = keyterm_in_text(tagged)

        if keyterm and not (ignore_definitions and
                            cls.is_definition(node, keyterm)):
            return keyterm

    @staticmethod
    def is_definition(node, keyterm):
        """A definition might be masquerading as a keyterm. Do not allow
        this"""
        included, excluded = Terms(None).node_definitions(node)
        terms = included + excluded
        keyterm_as_term = keyterm.lower()
        return any(ref.term == keyterm_as_term for ref in terms)

    def process(self, node):
        """ Get keyterms if we have text in the node that preserves the
        <E> tags. """
        keyterm = self.keyterm_in_node(node)
        if keyterm:
            return [{
                "key_term": keyterm,
                # The first instance of the key term is right one.
                "locations": [0]
            }]
