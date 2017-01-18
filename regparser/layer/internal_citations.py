# -*- coding: utf-8 -*-
import logging

from regparser.citations import Label, internal_citations
from regparser.layer.layer import Layer
from regparser.tree.struct import walk

logger = logging.getLogger(__name__)


class InternalCitationParser(Layer):
    shorthand = 'internal-citations'

    def __init__(self, tree, cfr_title, **context):
        super(InternalCitationParser, self).__init__(tree, **context)
        self.cfr_title = cfr_title
        self.known_citations = set()
        self.verify_citations = True

    def pre_process(self):
        """As a preprocessing step, run through the entire tree, collecting
        all labels."""
        def per_node(node):
            self.known_citations.add(tuple(node.label))
        walk(self.tree, per_node)

    def process(self, node):
        citations_list = self.parse(node.text,
                                    label=Label.from_node(node),
                                    title=str(self.cfr_title))
        if citations_list:
            return citations_list

    def remove_missing_citations(self, citations, text):
        """Remove any citations to labels we have not seen before (i.e.
        those collected in the pre_processing stage)"""
        final = []
        for c in citations:
            if tuple(c.label.to_list()) in self.known_citations:
                final.append(c)
            else:
                logger.warning("Missing citation? %s %r",
                               text[c.start:c.end], c.label)
                logger.debug("Context: %s", text)
        return final

    def parse(self, text, label, title=None):
        """ Parse the provided text, pulling out all the internal
        (self-referential) citations. """

        def to_layer(pc):
            return {'offsets': [(pc.start, pc.end)],
                    'citation': pc.label.to_list()}

        citations = internal_citations(text, label, require_marker=True,
                                       title=title)
        if self.verify_citations:
            citations = self.remove_missing_citations(citations, text)
        all_citations = [to_layer(c) for c in citations]

        return self.strip_whitespace(text, all_citations)

    @staticmethod
    def strip_whitespace(text, citations):
        """Modifies the offsets to exclude any trailing whitespace. Modifies
        the offsets in place."""
        for citation in citations:
            for i in range(len(citation['offsets'])):
                start, end = citation['offsets'][i]
                string = text[start:end]
                lstring = string.lstrip()
                rstring = string.rstrip()
                new_start = start + (len(string) - len(lstring))
                new_end = end - (len(string) - len(rstring))
                citation['offsets'][i] = (new_start, new_end)
        return citations
