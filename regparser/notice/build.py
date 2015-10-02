from collections import defaultdict

from lxml import etree

from regparser.notice import changes
from regparser.notice.address import fetch_addresses
from regparser.notice.build_appendix import parse_appendix_changes
from regparser.notice.build_interp import parse_interp_changes
from regparser.notice.diff import parse_amdpar, find_section, find_subpart
from regparser.notice.diff import new_subpart_added
from regparser.notice.diff import DesignateAmendment
from regparser.notice.dates import fetch_dates
from regparser.notice.sxs import find_section_by_section
from regparser.notice.sxs import build_section_by_section
from regparser.notice.util import spaces_then_remove, swap_emphasis_tags
from regparser.notice.xml import xmls_for_url
from regparser.tree import struct
from regparser.tree.xml_parser import reg_text
from regparser.grammar.unified import notice_cfr_p


def build_notice(cfr_title, cfr_part, fr_notice, do_process_xml=True):
    """Given JSON from the federal register, create our notice structure"""
    cfr_parts = set(str(ref['part']) for ref in fr_notice['cfr_references'])
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

    if fr_notice['full_text_xml_url'] and do_process_xml:
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
            elif amendment['action'] not in ('POST', 'PUT', 'RESERVE'):
                print 'NOT HANDLED: %s' % amendment['action']


def create_xml_changes(amended_labels, section, notice_changes):
    """For PUT/POST, match the amendments to the section nodes that got
    parsed, and actually create the notice changes. """

    def per_node(node):
        node.child_labels = [c.label_id() for c in node.children]
    struct.walk(section, per_node)

    amend_map = changes.match_labels_and_changes(amended_labels, section)

    for label, amendments in amend_map.iteritems():
        for amendment in amendments:
            if amendment['action'] in ('POST', 'PUT'):
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
                print 'NOT HANDLED: %s' % amendment['action']


class AmdparByParent(object):
    """Not all AMDPARs have a single REGTEXT/etc. section associated with them,
    particularly for interpretations/appendices. This simple class wraps those
    fields"""
    def __init__(self, parent, first_amdpar):
        self.parent = parent
        self.amdpars = [first_amdpar]

    def append(self, next_amdpar):
        self.amdpars.append(next_amdpar)


def process_amendments(notice, notice_xml):
    """ Process the changes to the regulation that are expressed in the notice.
    """
    amends = []
    notice_changes = changes.NoticeChanges()

    amdpars_by_parent = []
    for par in notice_xml.xpath('//AMDPAR'):
        parent = par.getparent()
        exists = filter(lambda aXp: aXp.parent == parent, amdpars_by_parent)
        if exists:
            exists[0].append(par)
        else:
            amdpars_by_parent.append(AmdparByParent(parent, par))

    default_cfr_part = notice['cfr_parts'][0]
    for aXp in amdpars_by_parent:
        amended_labels = []
        designate_labels, other_labels = [], []
        context = [aXp.parent.get('PART') or default_cfr_part]
        for par in aXp.amdpars:
            als, context = parse_amdpar(par, context)
            amended_labels.extend(als)

        labels_by_part = defaultdict(list)
        for al in amended_labels:
            if isinstance(al, DesignateAmendment):
                subpart_changes = process_designate_subpart(al)
                if subpart_changes:
                    notice_changes.update(subpart_changes)
                designate_labels.append(al)
            elif new_subpart_added(al):
                notice_changes.update(process_new_subpart(notice, al, par))
                designate_labels.append(al)
            else:
                other_labels.append(al)
                labels_by_part[al.label[0]].append(al)

        create_xmlless_changes(other_labels, notice_changes)

        for cfr_part, rel_labels in labels_by_part.iteritems():
            section_xml = find_section(par)
            if section_xml is not None:
                for section in reg_text.build_from_section(cfr_part,
                                                           section_xml):
                    create_xml_changes(rel_labels, section, notice_changes)

            for appendix in parse_appendix_changes(rel_labels, cfr_part,
                                                   aXp.parent):
                create_xml_changes(rel_labels, appendix, notice_changes)

            interp = parse_interp_changes(rel_labels, cfr_part, aXp.parent)
            if interp:
                create_xml_changes(rel_labels, interp, notice_changes)

        amends.extend(designate_labels)
        amends.extend(other_labels)

        if other_labels:    # Carry cfr_part through amendments
            default_cfr_part = other_labels[-1].label[0]

    if amends:
        notice['amendments'] = amends
        notice['changes'] = notice_changes.changes


def process_sxs(notice, notice_xml):
    """ Find and build SXS from the notice_xml. """
    sxs = find_section_by_section(notice_xml)
    # note we will continue to use cfr_parts[0] as the default SxS label until
    # we find a counter example
    sxs = build_section_by_section(sxs, notice['meta']['start_page'],
                                   notice['cfr_parts'][0])
    notice['section_by_section'] = sxs


def fetch_cfr_parts(notice_xml):
    """ Sometimes we need to read the CFR part numbers from the notice
        XML itself. This would need to happen when we've broken up a
        multiple-effective-date notice that has multiple CFR parts that
        may not be included in each date. """
    cfr_elm = notice_xml.xpath('//CFR')[0]
    results = notice_cfr_p.parseString(cfr_elm.text)
    return list(results)


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
