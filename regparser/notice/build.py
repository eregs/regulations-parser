from collections import defaultdict
import logging

from lxml import etree

from regparser.notice import changes
from regparser.notice.address import fetch_addresses
from regparser.notice.amdparser import amendment_from_xml, DesignateAmendment
from regparser.notice.build_appendix import parse_appendix_changes
from regparser.notice.build_interp import parse_interp_changes
from regparser.notice.changes import (
    find_section, find_subpart, new_subpart_added)
from regparser.notice.dates import fetch_dates
from regparser.notice.sxs import (
    build_section_by_section, find_section_by_section)
from regparser.notice.util import spaces_then_remove, swap_emphasis_tags
from regparser.notice.xml import fetch_cfr_parts, xmls_for_url
from regparser.tree import struct
from regparser.tree.xml_parser import reg_text


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

    if 'Subpart' in amendment.destination:
        subpart_changes = {}

        for label in amendment.labels:
            label_id = '-'.join(label)
            subpart_changes[label_id] = {
                'action': 'DESIGNATE', 'destination': amendment.destination}
        return subpart_changes


def process_new_subpart(notice, amd_label, par):
    """ A new subpart has been added, create the notice changes. """
    subpart_changes = {}
    subpart_xml = find_subpart(par)
    subpart = reg_text.build_subpart(amd_label.label[0], subpart_xml)

    for change in changes.create_subpart_amendment(subpart):
        subpart_changes.update(change)
    return subpart_changes


def create_xmlless_changes(amended_labels, notice_changes):
    """Deletes, moves, and the like do not have an associated XML structure.
    Add their changes"""
    amend_map = changes.match_labels_and_changes(amended_labels, None)
    for label, amendments in amend_map.iteritems():
        for amendment in amendments:
            if amendment['action'] == 'DELETE':
                notice_changes.update({label: {'action': amendment['action']}})
            elif amendment['action'] == 'MOVE':
                change = {'action': amendment['action']}
                destination = [d for d in amendment['destination'] if d != '?']
                change['destination'] = destination
                notice_changes.update({label: change})
            elif amendment['action'] not in ('POST', 'PUT', 'RESERVE',
                                             'INSERT'):
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
                    notice_changes.update(n)
            elif amendment['action'] == 'RESERVE':
                change = changes.create_reserve_amendment(amendment)
                notice_changes.update(change)
            elif amendment['action'] not in ('DELETE', 'MOVE'):
                logger.warning("Unknown action: %s", amendment['action'])


def process_amendments(notice, notice_xml):
    """Process changes to the regulation that are expressed in the notice."""
    all_amends = []     # will be added to the notice
    cfr_part = notice['cfr_parts'][0]
    notice_changes = changes.NoticeChanges()

    # process amendments in batches, based on their parent XML
    for amdparent in notice_xml.xpath('//AMDPAR/..'):
        context = [amdparent.get('PART') or cfr_part]
        amendments_by_section = defaultdict(list)
        normal_amends = []  # amendments not moving or adding a subpart
        for amdpar in amdparent.xpath('.//AMDPAR'):
            instructions = amdpar.xpath('./EREGS_INSTRUCTIONS')
            if not instructions:
                logger.warning('No <EREGS_INSTRUCTIONS>. Was this notice '
                               'preprocessed?')
                continue
            instructions = instructions[0]
            amendments = [amendment_from_xml(el) for el in instructions]
            context = [None if l is '?' else l
                       for l in instructions.get('final_context').split('-')]
            section_xml = find_section(amdpar)
            for amendment in amendments:
                all_amends.append(amendment)
                if isinstance(amendment, DesignateAmendment):
                    subpart_changes = process_designate_subpart(amendment)
                    if subpart_changes:
                        notice_changes.update(subpart_changes)
                elif new_subpart_added(amendment):
                    notice_changes.update(process_new_subpart(
                        notice, amendment, amdpar))
                elif section_xml is None:
                    normal_amends.append(amendment)
                else:
                    normal_amends.append(amendment)
                    amendments_by_section[section_xml].append(amendment)

        cfr_part = context[0]   # carry the part through to the next amdparent
        create_xmlless_changes(normal_amends, notice_changes)
        # Process amendments relating to a specific section in batches, too
        for section_xml, related_amends in amendments_by_section.items():
            for section in reg_text.build_from_section(cfr_part, section_xml):
                create_xml_changes(related_amends, section, notice_changes)

        for appendix in parse_appendix_changes(normal_amends, cfr_part,
                                               amdparent):
            create_xml_changes(normal_amends, appendix, notice_changes)

        interp = parse_interp_changes(normal_amends, cfr_part, amdparent)
        if interp:
            create_xml_changes(normal_amends, interp, notice_changes)

    if all_amends:
        notice['amendments'] = all_amends
        notice['changes'] = notice_changes.changes

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
