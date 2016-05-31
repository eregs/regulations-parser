import logging
import string

from pyparsing import Optional, Suppress, Word

from regparser.grammar.utils import QuickSearchable
from regparser.layer.layer import Layer

logger = logging.getLogger(__name__)


level1 = Word("IVXLCDM").leaveWhitespace().setResultsName("l1")
level2 = Word(string.ascii_uppercase).leaveWhitespace().setResultsName("l2")
level3 = Word(string.digits).leaveWhitespace().setResultsName("l3")
level4 = Word(string.ascii_lowercase).leaveWhitespace().setResultsName("l4")
level5 = Word("ivxlcdm").leaveWhitespace().setResultsName("l5")
level6 = Word(string.ascii_lowercase).leaveWhitespace().setResultsName("l6")
period = Suppress(".").leaveWhitespace()

# e.g. I.B, I.B.3, I.B.3.d, I.B.3.d.v, I.B.3.d.v.f
citation = level1 + period + level2 + Optional(period + level3 + Optional(
    period + level4 + Optional(period + level5 + Optional(period + level6))))
citation = QuickSearchable(citation)


class InternalCitations(Layer):
    shorthand = 'internal-citations'

    def __init__(self, tree, **context):
        super(InternalCitations, self).__init__(tree, **context)
        self.known_citations = set()

    def pre_process(self):
        """As a preprocessing step, run through the entire tree, collecting
        all labels"""
        labels = self.tree.walk(lambda node: tuple(node.label))
        self.known_citations = set(labels)

    def process(self, node):
        """Find citations to elements within this preamble"""
        results = []
        for match, start, end in citation.scanString(node.text):
            label = tuple(self.tree.label[:1] + list(match))
            if label in self.known_citations:
                results.append({'offsets': [(start, end)],
                                'citation': label})
            else:
                logger.warning("Missing citation? %s %r",
                               node.text[start:end], label)
                logger.debug("Context: %s", node.text)
        return results or None      # "None" for consistency with other layers
