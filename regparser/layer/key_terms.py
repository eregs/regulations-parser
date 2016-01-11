import hashlib
import re

from layer import Layer
from regparser.layer.paragraph_markers import marker_of
from regparser.layer.terms import Terms


def eliminate_extras(keyterm):
    """ The XML <E> tags that indicate keyterms are also used
    for italics. So, phrases such as 'See' and 'See also' are included
    sometimes in the keyterm. We eliminate that here. """

    extras = [' See also', ' See']
    for extra in extras:
        if keyterm.endswith(extra):
            keyterm = keyterm[:-len(extra)]
    return keyterm


_NONWORDS = re.compile(r'\W+')


def keyterm_to_int(keyterm):
    """Hash a keyterm's text and convert it into an integer. We'll trim to
    just 8 hex characters for legibility. We don't need to fear hash
    collisions as we'll have 16**8 ~ 4 billion possibilities. The birthday
    paradox tells us we'd only expect collisions after ~ 60 thousand entries.
    We're expecting at most a few hundred"""
    phrase = _NONWORDS.sub('', keyterm.lower())
    hashed = hashlib.sha1(phrase).hexdigest()[:8]
    return int(hashed, 16)


class KeyTerms(Layer):
    PATTERN = re.compile(ur'.*?<E T="03">([^<]*?)</E>.*?', re.UNICODE)

    @staticmethod
    def process_node_text(node):
        """Take a paragraph, remove the marker, and extraneous whitespaces."""
        marker = marker_of(node) or ''
        text = node.tagged_text

        text = text.replace(marker, '', 1).strip()
        return text

    @staticmethod
    def keyterm_is_first(node, keyterm):
        """ The keyterm should be the first phrase in the paragraph. """
        node_text = KeyTerms.process_node_text(node)
        start = node_text.find(keyterm)
        tag_length = len("<E T='03'>")

        return start == tag_length

    @staticmethod
    def get_keyterm(node, ignore_definitions=True):
        match = KeyTerms.PATTERN.match(getattr(node, 'tagged_text', ''))
        keyterm = match.groups()[0] if match else None
        if keyterm and KeyTerms.keyterm_is_first(node, keyterm):
            if ignore_definitions:
                return KeyTerms.remove_definition_keyterm(node, keyterm)
            return keyterm

    @staticmethod
    def remove_definition_keyterm(node, keyterm):
        """A definition might be masquerading as a keyterm. Do not allow
        this"""
        included, excluded = Terms(None).node_definitions(node)
        terms = included + excluded
        keyterm_as_term = keyterm.lower()
        if not any(ref.term == keyterm_as_term for ref in terms):
            return keyterm

    def process(self, node):
        """ Get keyterms if we have text in the node that preserves the
        <E> tags. """
        if hasattr(node, 'tagged_text'):
            keyterm = KeyTerms.get_keyterm(node)
            if keyterm:
                keyterm = eliminate_extras(keyterm)
                layer_el = [{
                    "key_term": keyterm,
                    # The first instance of the key term is right one.
                    "locations": [0]}]
                return layer_el
