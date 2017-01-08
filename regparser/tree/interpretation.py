import logging
from itertools import takewhile

from regparser.citations import internal_citations
from regparser.grammar import unified
from regparser.tree.struct import Node

logger = logging.getLogger(__name__)


def merge_labels(labels):
    max_len = max(len(l) for l in labels)
    labels = [l + [None] * (max_len - len(l)) for l in labels]
    final_label = []
    for tups in zip(*labels):
        final_label.append('_'.join(sorted(set(tups))))
    return final_label


def text_to_labels(text, initial_label, warn=True, force_start=False):
    """Convert header text used in interpretations into the interpretation
    label associated with them (e.g. 22(a) becomes XXX-22-a-Interp).
    warn: lets us know if there was an error in the conversion.
    force_start: ensure that the citations is at the *beginning* of the
                 text"""
    all_citations = internal_citations(text.strip(), initial_label)
    all_citations = sorted(all_citations, key=lambda c: c.start)

    #   We care only about the first citation and its clauses
    citations = all_citations[:1]
    if force_start:
        citations = [c for c in citations if c.full_start == 0]

    #   Under certain situations, we need to infer from context
    initial_pars = [match
                    for match, start, _ in unified.any_depth_p.scanString(text)
                    if start == 0]

    if citations:
        if citations[0].in_clause:
            #   Clauses still in the first conjunction
            citations.extend(takewhile(lambda c: c.in_clause,
                                       all_citations[1:]))

        return [citation.label.to_list() + [Node.INTERP_MARK]
                for citation in citations]
    elif (initial_label.comment and initial_pars and
          initial_label.settings.get('appendix')):
        return [[initial_label.settings['part'],
                 initial_label.settings['appendix']] +
                list(initial_pars[0]) +
                [Node.INTERP_MARK]]
    elif warn:
        logger.warning("Couldn't turn into label: " + text)
    return []
