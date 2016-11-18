# -*- coding: utf-8 -*-
from collections import namedtuple
from copy import deepcopy
import logging
from itertools import dropwhile

from lxml import etree

from regparser.notice import changes, util
from regparser.notice.amdparser import amendment_from_xml
from regparser.tree.struct import Node, walk
from regparser.tree.xml_parser import interpretations
from regparser.tree.xml_parser.appendices import process_appendix
from regparser.tree.xml_parser.reg_text import (
    build_from_section, build_subpart)


logger = logging.getLogger(__name__)
Content = namedtuple('Content', ['struct', 'amends'])


class ContentCache(object):
    """As we can expect several amending instructions to refer to the same
    section/appendix/etc., this object exists so that we only parse chunks of
    relevant XML once."""
    def __init__(self):
        self.by_xml = {}

    def fetch(self, key, fn, *args):
        """Check the cache; if not present, run fn with the given args"""
        if key is not None and key not in self.by_xml:
            self.by_xml[key] = Content(fn(*args), [])
        return self.by_xml.get(key)

    def content_of_change(self, instruction_xml):
        """Instructions which create or modify a chunk of the CFR need to know
        not only which paragraphs are being modified, but the _content_ of
        those modifications. This method searches the XML around the
        instruction and attempts to derive a related Node"""
        is_editing = instruction_xml.tag in ('POST', 'PUT', 'INSERT',
                                             'RESERVE')
        label = instruction_xml.get('label', '')
        label_parts = label.split('-')
        cfr_part = label_parts[0]

        # <AMDPAR><EREGS_INSTRUCTIONS><INSTRUCTION>...
        amdpar = instruction_xml.getparent().getparent()
        new_subpart = (instruction_xml.tag == 'POST' and
                       len(label_parts) == 2 and 'Subpart:' in label_parts[1])

        if not is_editing:
            return None
        elif new_subpart:
            xml = find_subpart(amdpar)
            return self.fetch(xml, build_subpart, cfr_part, xml)
        elif 'Appendix' in label:
            xml = amdpar.getparent()
            letter = label_parts[1][len('Appendix:'):]
            return self.fetch(xml, parse_appendix, xml, cfr_part, letter)
        elif 'Interpretations' in label:
            xml = amdpar.getparent()
            return self.fetch(xml, parse_interp, cfr_part, xml)
        else:
            xml = find_section(amdpar)
            return self.fetch(xml, parse_regtext, xml, cfr_part)


def parse_regtext(xml, cfr_part):
    """Small wrapper around build_from_section that returns only one section"""
    sections = build_from_section(cfr_part, xml)
    if sections:
        return sections[0]


def parse_appendix(xml, cfr_part, letter):
    """Attempt to parse an appendix. Used when the entire appendix has been
    replaced/added or when we can use the section headers to determine our
    place. If the format isn't what we expect, display a warning."""
    xml = deepcopy(xml)
    hds = xml.xpath('//HD[contains(., "Appendix %s to Part %s")]'
                    % (letter, cfr_part))
    if len(hds) == 0:
        logger.warning("Could not find Appendix %s to part %s",
                       letter, cfr_part)
    elif len(hds) > 1:
        logger.warning("Too many headers for %s to part %s",
                       letter, cfr_part)
    else:
        hd = hds[0]
        hd.set('SOURCE', 'HED')
        extract = hd.getnext()
        if extract is not None and extract.tag == 'EXTRACT':
            extract.insert(0, hd)
            for trailing in dropwhile(lambda n: n.tag != 'AMDPAR',
                                      extract.getchildren()):
                extract.remove(trailing)
            return process_appendix(extract, cfr_part)
        logger.warning("Bad format for whole appendix")


def parse_interp(cfr_part, parent_xml):
    """Figure out which parts of the parent_xml are relevant to
    interpretations. Pass those on to interpretations.parse_from_xml and
    return the results"""
    parent_xml = standardize_interp_xml(parent_xml)

    # Skip over everything until 'Supplement I' in a header
    seen_header = False
    xml_nodes = []

    def contains_supp(n):
        text = (n.text or '').lower()
        return 'supplement i' in text

    for child in parent_xml:
        # SECTION shouldn't be in this part of the XML, but often is. Expand
        # it to proceed
        if seen_header and child.tag == 'SECTION':
            sectno = child.xpath('./SECTNO')[0]
            subject = child.xpath('./SUBJECT')[0]
            header = etree.Element("HD", SOURCE="HD2")
            header.text = sectno.text + u'—' + subject.text
            child.insert(child.index(sectno), header)
            child.remove(sectno)
            child.remove(subject)
            xml_nodes.extend(child.getchildren())
        elif seen_header:
            xml_nodes.append(child)
        else:
            if child.tag == 'HD' and contains_supp(child):
                seen_header = True
            if any(contains_supp(c) for c in child.xpath(".//HD")):
                seen_header = True

    root = Node(label=[cfr_part, Node.INTERP_MARK], node_type=Node.INTERP)
    root = interpretations.parse_from_xml(root, xml_nodes)
    if not root.children:
        return None
    else:
        return root


def standardize_interp_xml(xml):
    """We will assume a format of Supplement I header followed by HDs,
    STARS, and Ps, so move anything in an EXTRACT up a level"""
    xml = util.spaces_then_remove(deepcopy(xml), 'PRTPAGE')
    for extract in xml.xpath(".//EXTRACT|.//APPENDIX|.//SUBPART"):
        ex_parent = extract.getparent()
        idx = ex_parent.index(extract)
        for child in extract:
            ex_parent.insert(idx, child)
            idx += 1
        ex_parent.remove(extract)
    return xml


def fix_section_node(paragraphs, amdpar_xml):
    """ When notices are corrected, the XML for notices doesn't follow the
    normal syntax. Namely, pargraphs aren't inside section tags. We fix that
    here, by finding the preceding section tag and appending paragraphs to it.
    """

    sections = [s for s in amdpar_xml.itersiblings(preceding=True)
                if s.tag == 'SECTION']

    # Let's only do this if we find one section tag.
    if len(sections) == 1:
        section = deepcopy(sections[0])
        for paragraph in paragraphs:
            section.append(deepcopy(paragraph))
        return section


def find_lost_section(amdpar_xml):
    """ This amdpar doesn't have any following siblings, so we
    look in the next regtext """
    reg_text = amdpar_xml.getparent()
    reg_text_siblings = [s for s in reg_text.itersiblings()
                         if s.tag == 'REGTEXT']
    if len(reg_text_siblings) > 0:
        candidate_reg_text = reg_text_siblings[0]
        amdpars = [a for a in candidate_reg_text if a.tag == 'AMDPAR']
        if len(amdpars) == 0:
            # Only do this if there are not AMDPARS
            for c in candidate_reg_text:
                if c.tag == 'SECTION':
                    return c


def find_section(amdpar_xml):
    """ With an AMDPAR xml, return the first section sibling """
    siblings = [s for s in amdpar_xml.itersiblings()]

    if len(siblings) == 0:
        return find_lost_section(amdpar_xml)

    for sibling in siblings:
        if sibling.tag == 'SECTION':
            return sibling

    paragraphs = [s for s in siblings if s.tag == 'P']
    if len(paragraphs) > 0:
        return fix_section_node(paragraphs, amdpar_xml)


def find_subpart(amdpar_tag):
    """ Look amongst an amdpar tag's siblings to find a subpart. """
    for sibling in amdpar_tag.itersiblings():
        if sibling.tag == 'SUBPART':
            return sibling


def fetch_amendments(notice_xml):
    """Process changes to the regulation that are expressed in the notice."""
    notice_changes = changes.NoticeChanges()

    if notice_xml.xpath('.//AMDPAR[not(EREGS_INSTRUCTIONS)]'):
        logger.warning(
            'No <EREGS_INSTRUCTIONS>. Was this notice preprocessed?')

    cache = ContentCache()
    authority_by_xml = {}
    for instruction_xml in notice_xml.xpath('.//EREGS_INSTRUCTIONS/*'):
        amendment = amendment_from_xml(instruction_xml)
        content = cache.content_of_change(instruction_xml)
        if instruction_xml.tag == 'MOVE_INTO_SUBPART':
            subpart_changes = process_designate_subpart(amendment)
            if subpart_changes:
                notice_changes.add_changes(amendment.amdpar_xml,
                                           subpart_changes)
        elif instruction_xml.tag == 'AUTHORITY':
            authority_by_xml[amendment.amdpar_xml] = instruction_xml.text
        elif changes.new_subpart_added(amendment):
            subpart_changes = {}
            for change in changes.create_subpart_amendment(content.struct):
                subpart_changes.update(change)
            notice_changes.add_changes(amendment.amdpar_xml, subpart_changes)
        elif content:
            content.amends.append(amendment)
        else:
            create_xmlless_change(amendment, notice_changes)

    for content in cache.by_xml.values():
        create_xml_changes(content.amends, content.struct, notice_changes)

    amendments = []
    for amdpar_xml in notice_xml.xpath('.//AMDPAR'):
        amendment_dict = {"instruction": amdpar_xml.text}
        # There'll be at most one
        for inst_xml in amdpar_xml.xpath('./EREGS_INSTRUCTIONS'):
            context = inst_xml.get('final_context', '')
            amendment_dict['cfr_part'] = context.split('-')[0]
        relevant_changes = notice_changes.changes_by_xml[amdpar_xml]
        if relevant_changes:
            amendment_dict['changes'] = list(relevant_changes.items())
        if amdpar_xml in authority_by_xml:
            amendment_dict['authority'] = authority_by_xml[amdpar_xml]

        amendments.append(amendment_dict)

    return amendments


def process_designate_subpart(amendment):
    """ Process the designate amendment if it adds a subpart. """
    label_id = '-'.join(amendment.label)
    return {label_id: {'action': 'DESIGNATE',
                       'destination': amendment.destination}}


def create_xmlless_change(amendment, notice_changes):
    """Deletes, moves, and the like do not have an associated XML structure.
    Add their changes"""
    amend_map = changes.match_labels_and_changes([amendment], None)
    for label, amendments in amend_map.items():
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
    walk(section, per_node)

    amend_map = changes.match_labels_and_changes(amended_labels, section)

    for label, amendments in amend_map.items():
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
