import logging

from lxml import etree

from regparser.grammar.unified import notice_cfr_p
from regparser.notice.amendments.fetch import fetch_amendments
from regparser.notice.dates import fetch_dates
from regparser.notice.sxs import (build_section_by_section,
                                  find_section_by_section)
from regparser.notice.util import spaces_then_remove, swap_emphasis_tags
from regparser.notice.xml import xmls_for_url

logger = logging.getLogger(__name__)


def build_notice(cfr_title, cfr_part, fr_notice, fetch_xml=True,
                 xml_to_process=None):
    """Given JSON from the federal register, create our notice structure"""
    cfr_parts = {str(ref['part']) for ref in fr_notice['cfr_references']}
    if cfr_part:
        cfr_parts.add(cfr_part)
    notice = {'cfr_title': cfr_title, 'cfr_parts': list(cfr_parts)}
    #   Copy over most fields
    for field in ['comments_close_on', 'document_number', 'publication_date',
                  'regulation_id_numbers']:
        if fr_notice[field]:
            notice[field] = fr_notice[field]

    if fr_notice['effective_on']:
        notice['effective_on'] = fr_notice['effective_on']
        notice['initial_effective_on'] = fr_notice['effective_on']

    if fr_notice['html_url']:
        notice['fr_url'] = fr_notice['html_url']

    if fr_notice['citation']:
        notice['fr_citation'] = fr_notice['citation']

    notice['fr_volume'] = fr_notice['volume']
    notice['meta'] = {}
    for key in ('dates', 'end_page', 'start_page', 'type'):
        notice['meta'][key] = fr_notice[key]

    if xml_to_process is not None:
        return [process_xml(notice, xml_to_process)]
    elif fr_notice['full_text_xml_url'] and fetch_xml:
        xmls = xmls_for_url(fr_notice['full_text_xml_url'])
        notices = [process_xml(notice, xml) for xml in xmls]
        set_document_numbers(notices)
        return notices
    return [notice]


def split_doc_num(doc_num, effective_date):
    """ If we have a split notice, we construct a document number
    based on the original document number and the effective date. """
    effective_date = ''.join(effective_date.split('-'))
    return '{0}_{1}'.format(doc_num, effective_date)


def set_document_numbers(notices):
    """If we have multiple notices (due to being split across multiple
    effective dates,) we need to fix their document numbers."""

    if len(notices) > 1:
        for notice in notices:
            notice['document_number'] = split_doc_num(
                notice['document_number'], notice['effective_on'])
    return notices


def process_sxs(notice, notice_xml):
    """ Find and build SXS from the notice_xml. """
    sxs = find_section_by_section(notice_xml)
    # note we will continue to use cfr_parts[0] as the default SxS label until
    # we find a counter example
    sxs = build_section_by_section(sxs, notice['meta']['start_page'],
                                   notice['cfr_parts'][0])
    notice['section_by_section'] = sxs


# @todo - this can be deleted once we remove process_xml
def fetch_cfr_parts(notice_xml):
    """ Sometimes we need to read the CFR part numbers from the notice
        XML itself. This would need to happen when we've broken up a
        multiple-effective-date notice that has multiple CFR parts that
        may not be included in each date. """
    parts = []
    for cfr_elm in notice_xml.xpath('//CFR'):
        parts.extend(notice_cfr_p.parseString(cfr_elm.text).cfr_parts)
    return list(sorted(set(parts)))


def process_xml(notice, notice_xml):
    """Pull out relevant fields from the xml and add them to the notice"""
    notice = dict(notice)   # defensive copy

    if not notice.get('effective_on'):
        dates = fetch_dates(notice_xml)
        if dates and 'effective' in dates:
            notice['effective_on'] = dates['effective'][0]

    if not notice.get('cfr_parts'):
        cfr_parts = fetch_cfr_parts(notice_xml)
        notice['cfr_parts'] = cfr_parts

    process_sxs(notice, notice_xml)
    amds = fetch_amendments(notice_xml)
    if amds:
        notice['amendments'] = amds
    add_footnotes(notice, notice_xml)

    return notice


def add_footnotes(notice, notice_xml):
    """ Parse the notice xml for footnotes and add them to the notice. """
    notice['footnotes'] = {}
    for child in notice_xml.xpath('//FTNT/*'):
        spaces_then_remove(child, 'PRTPAGE')
        swap_emphasis_tags(child)

        ref = child.xpath('.//SU')
        if ref:
            child.text = ref[0].tail
            child.remove(ref[0])
            content = child.text
            for cc in child:
                content += etree.tounicode(cc)
            if child.tail:
                content += child.tail
            notice['footnotes'][ref[0].text] = content.strip()
