# -*- coding: utf-8 -*-
import logging
from collections import namedtuple

from regparser.notice import changes
from regparser.notice.amdparser import amendment_from_xml
from regparser.notice.amendments.subpart import process_designate_subpart
from regparser.plugins import instantiate_if_possible
from regparser.tree.struct import walk

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

        if not is_editing:
            return None

        for extension in instantiate_if_possible(
                'eregs_ns.parser.amendment.content'):
            result = extension(instruction_xml)
            if result:
                key, fn = result
                if key is not None and key not in self.by_xml:
                    self.by_xml[key] = Content(fn(), [])
                return self.by_xml.get(key)


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
            change = process_designate_subpart(amendment)
            notice_changes.add_change(amendment.amdpar_xml, change)
        elif instruction_xml.tag == 'AUTHORITY':
            authority_by_xml[amendment.amdpar_xml] = instruction_xml.text
        elif changes.new_subpart_added(amendment):
            for change in changes.create_subpart_amendment(content.struct):
                notice_changes.add_change(amendment.amdpar_xml, change)
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
        relevant_changes = notice_changes[amdpar_xml]
        if relevant_changes:
            amendment_dict['changes'] = list(relevant_changes.items())
        if amdpar_xml in authority_by_xml:
            amendment_dict['authority'] = authority_by_xml[amdpar_xml]

        amendments.append(amendment_dict)

    return amendments


def create_xmlless_change(amendment, notice_changes):
    """Deletes, moves, and the like do not have an associated XML structure.
    Add their changes"""
    amend_map = changes.match_labels_and_changes([amendment], None)
    for label, amendments in amend_map.items():
        for amendment in amendments:
            if amendment['action'] == 'DELETE':
                notice_changes.add_change(
                    amendment['amdpar_xml'],
                    changes.Change(label, {'action': amendment['action']}))
            elif amendment['action'] == 'MOVE':
                change = {'action': amendment['action']}
                destination = [d for d in amendment['destination'] if d != '?']
                change['destination'] = destination
                notice_changes.add_change(
                    amendment['amdpar_xml'], changes.Change(label, change))
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
                    notice_changes.add_change(amendment['amdpar_xml'], n)
            elif amendment['action'] == 'RESERVE':
                change = changes.create_reserve_amendment(amendment)
                notice_changes.add_change(amendment['amdpar_xml'], change)
            else:
                logger.warning("Unknown action: %s", amendment['action'])
