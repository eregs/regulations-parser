from collections import namedtuple
from datetime import date
from itertools import dropwhile, takewhile

from regparser.grammar.delays import tokenizer as delay_tokenizer
from regparser.grammar.delays import Delayed, EffectiveDate, Notice


class FRDelay(namedtuple('FRDelay', ['volume', 'page', 'delayed_until'])):
    def modifies_notice(self, notice):
        """Calculate whether the fr citation is within the provided notice"""
        return (notice['fr_volume'] == self.volume and
                notice['meta']['start_page'] <= self.page and
                notice['meta']['end_page'] >= self.page)

    def modifies_notice_xml(self, notice_xml):
        """Calculates whether the fr citation is within the provided
        NoticeXML"""
        return (notice_xml.fr_volume == self.volume and
                notice_xml.start_page <= self.page and
                notice_xml.end_page >= self.page)


def modify_effective_dates(notices):
    """The effective date of notices can be delayed by other notices. We
    make sure to modify such notices as appropriate."""

    #   Sort so that later modifications supersede earlier ones
    notices = sorted(notices, key=lambda n: n['publication_date'])
    #   Look for modifications to effective date
    for notice in notices:
        #   Only final rules can change effective dates
        if notice['meta']['type'] != 'Rule':
            continue
        if not notice['meta']['dates']:
            continue
        for delay in (delay for sent in notice['meta']['dates'].split('.')
                      for delay in delays_in_sentence(sent)):
            for delayed in filter(delay.modifies_notice, notices):
                delayed['effective_on'] = unicode(delay.delayed_until)


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
    frs = [t for t in frs if isinstance(t, Notice)]

    if not frs or not tokens:
        return []
    #   Remove the "delayed"
    tokens = tokens[1:]

    tokens = [t for t in tokens if isinstance(t, date)]
    changed_to = None
    if tokens:
        changed_to = tokens[-1]
    return [FRDelay(fr.volume, fr.page, changed_to) for fr in frs]
