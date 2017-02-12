from collections import namedtuple
from datetime import date
from itertools import dropwhile, takewhile

from regparser.grammar.delays import tokenizer as delay_tokenizer
from regparser.grammar.delays import Delayed, EffectiveDate
from regparser.notice.citation import Citation as NoticeCitation


class FRDelay(namedtuple('FRDelay', ['volume', 'page', 'delayed_until'])):
    def modifies_notice_xml(self, notice_xml):
        """Calculates whether the fr citation is within the provided
        NoticeXML"""
        return (notice_xml.fr_volume == self.volume and
                notice_xml.start_page <= self.page and
                notice_xml.end_page >= self.page)


def delays_in_sentence(sent):
    """Tokenize the provided sentence and check if it is a format that
    indicates that some notices have changed. This format is:
    ... "effective date" ... FRNotices ... "delayed" ... (UntilDate)"""
    tokens = [token[0] for token, _, _ in delay_tokenizer.scanString(sent)]
    tokens = list(dropwhile(lambda t: not isinstance(t, EffectiveDate),
                            tokens))
    if not tokens:
        return []
    #   Remove the "effective date"
    tokens = tokens[1:]

    frs = list(takewhile(lambda t: not isinstance(t, Delayed), tokens))
    tokens = tokens[len(frs):]
    frs = [t for t in frs if isinstance(t, NoticeCitation)]

    if not frs or not tokens:
        return []
    #   Remove the "delayed"
    tokens = tokens[1:]

    tokens = [t for t in tokens if isinstance(t, date)]
    changed_to = None
    if tokens:
        changed_to = tokens[-1]
    return [FRDelay(fr.volume, fr.page, changed_to) for fr in frs]
