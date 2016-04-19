import logging

from lxml import etree

from regparser.notice import changes
from regparser.notice.address import fetch_addresses
from regparser.notice.amdparser import amendment_from_xml
from regparser.notice.amendments import ContentCache
from regparser.notice.changes import new_subpart_added
from regparser.notice.dates import fetch_dates
from regparser.notice.sxs import (
    build_section_by_section, find_section_by_section)
from regparser.notice.util import spaces_then_remove, swap_emphasis_tags
from regparser.notice.xml import fetch_cfr_parts, xmls_for_url
from regparser.tree import struct


logger = logging.getLogger(__name__)


def build_notice(cfr_title, cfr_part, fr_notice, fetch_xml=True,
                 xml_to_process=None):
    """Given JSON from the federal register, create our notice structure"""
    cfr_parts = set(str(ref['part']) for ref in fr_notice['cfr_references'])
    if cfr_part:
        cfr_parts.add(cfr_part)
    notice = {'cfr_title': cfr_title, 'cfr_parts': list(cfr_parts)}
    #   Copy over most fields
    for field in ['abstract', 'action', 'agency_names', 'comments_close_on',
                  'document_number', 'publication_date',
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
    return '%s_%s' % (doc_num, effective_date)


def set_document_numbers(notices):
    """If we have multiple notices (due to being split across multiple
    effective dates,) we need to fix their document numbers."""

    if len(notices) > 1:
        for notice in notices:
            notice['document_number'] = split_doc_num(
                notice['document_number'], notice['effective_on'])
    return notices


def process_designate_subpart(amendment):
    """ Process the designate amendment if it adds a subpart. """
    label_id = '-'.join(amendment.label)
    return {label_id: {'action': 'DESIGNATE',
                       'destination': amendment.destination}}


def create_xmlless_changes(amendment, notice_changes):
    """Deletes, moves, and the like do not have an associated XML structure.
    Add their changes"""
    amend_map = changes.match_labels_and_changes([amendment], None)
    for label, amendments in amend_map.iteritems():
        for amendment in amendments:
            if amendment['action'] == 'DELETE':
                notice_changes.add_changes(
                    amendment['amdpar_xml'],
                    {label: {'action': amendment['action']}})
            elif amendment['action'] == 'MOVE':
                change = {'action': amendment['action']}
                destination = [d for d in amendment['destination'] if d != '?']
                change['destination'] = destination
                notice_changes.add_changes(
                    amendment['amdpar_xml'], {label: change})
            else:
                logger.warning("Unknown action: %s", amendment['action'])


def create_xml_changes(amended_labels, section, notice_changes):
    """For PUT/POST, match the amendments to the section nodes that got
    parsed, and actually create the notice changes. """

    def per_node(node):
        node.child_labels = [c.label_id() for c in node.children]
    struct.walk(section, per_node)

    amend_map = changes.match_labels_and_changes(amended_labels, section)

    for label, amendments in amend_map.iteritems():
        for amendment in amendments:
            if amendment['action'] in ('POST', 'PUT', 'INSERT'):
                if 'field' in amendment:
                    nodes = changes.create_field_amendment(label, amendment)
                else:
                    nodes = changes.create_add_amendment(amendment)
                for n in nodes:
                    notice_changes.add_changes(amendment['amdpar_xml'], n)
            elif amendment['action'] == 'RESERVE':
                change = changes.create_reserve_amendment(amendment)
                notice_changes.add_changes(amendment['amdpar_xml'], change)
            else:
                logger.warning("Unknown action: %s", amendment['action'])


def process_amendments(notice, notice_xml):
    """Process changes to the regulation that are expressed in the notice."""
    notice_changes = changes.NoticeChanges()

    if notice_xml.xpath('.//AMDPAR[not(EREGS_INSTRUCTIONS)]'):
        logger.warning(
            'No <EREGS_INSTRUCTIONS>. Was this notice preprocessed?')

    cache = ContentCache()
    batch = {}
    for instruction_xml in notice_xml.xpath('.//EREGS_INSTRUCTIONS/*'):
        struct = cache.content_of_change(instruction_xml)
        amendment = amendment_from_xml(instruction_xml)
        if instruction_xml.tag == 'MOVE_INTO_SUBPART':
            subpart_changes = process_designate_subpart(amendment)
            if subpart_changes:
                notice_changes.add_changes(amendment.amdpar_xml, changes)
        elif new_subpart_added(amendment):
            subpart_changes = {}
            for change in changes.create_subpart_amendment(struct):
                subpart_changes.update(change)
            notice_changes.add_changes(amendment.amdpar_xml, subpart_changes)
        elif not struct:
            create_xmlless_changes(amendment, notice_changes)
        else:
            key = '-'.join(struct.label)
            if key not in batch:
                batch[key] = {'struct': struct, 'amends': []}
            batch[key]['amends'].append(amendment)

    for d in batch.values():
        create_xml_changes(d['amends'], d['struct'], notice_changes)

    amendments = []
    for amdpar_xml in notice_xml.xpath('.//AMDPAR'):
        amendment = {"instruction": amdpar_xml.text}
        relevant_changes = notice_changes.changes_by_xml[amdpar_xml]
        if relevant_changes:
            amendment['changes'] = list(relevant_changes.items())

        amendments.append(amendment)

    if amendments:
        notice['amendments'] = amendments

    return notice


def process_sxs(notice, notice_xml):
    """ Find and build SXS from the notice_xml. """
    sxs = find_section_by_section(notice_xml)
    # note we will continue to use cfr_parts[0] as the default SxS label until
    # we find a counter example
    sxs = build_section_by_section(sxs, notice['meta']['start_page'],
                                   notice['cfr_parts'][0])
    notice['section_by_section'] = sxs


def process_xml(notice, notice_xml):
    """Pull out relevant fields from the xml and add them to the notice"""
    notice = dict(notice)   # defensive copy

    xml_chunk = notice_xml.xpath('//FURINF/P')
    if xml_chunk:
        notice['contact'] = xml_chunk[0].text

    addresses = fetch_addresses(notice_xml)
    if addresses:
        notice['addresses'] = addresses

    if not notice.get('effective_on'):
        dates = fetch_dates(notice_xml)
        if dates and 'effective' in dates:
            notice['effective_on'] = dates['effective'][0]

    if not notice.get('cfr_parts'):
        cfr_parts = fetch_cfr_parts(notice_xml)
        notice['cfr_parts'] = cfr_parts

    process_sxs(notice, notice_xml)
    process_amendments(notice, notice_xml)
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
                content += etree.tostring(cc)
            if child.tail:
                content += child.tail
            notice['footnotes'][ref[0].text] = content.strip()
