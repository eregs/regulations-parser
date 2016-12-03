# -*- coding: utf-8 -*-
import logging

from lxml import etree

from regparser import content
from regparser.tree import reg_text
from regparser.tree.struct import Node
from regparser.tree.xml_parser import tree_utils
from regparser.tree.gpo_cfr.appendices import build_non_reg_text
from regparser.tree.gpo_cfr.section import build_from_section


logger = logging.getLogger(__name__)


def get_reg_part(reg_doc):
    """
    Depending on source, the CFR part number exists in different places. Fetch
    it, wherever it is.
    """

    potential_parts = []
    potential_parts.extend(
        # FR notice
        node.attrib['PART'] for node in reg_doc.xpath('//REGTEXT'))
    potential_parts.extend(
        # e-CFR XML, under PART/EAR
        node.text.replace('Pt.', '').strip()
        for node in reg_doc.xpath('//PART/EAR')
        if 'Pt.' in node.text)
    potential_parts.extend(
        # e-CFR XML, under FDSYS/HEADING
        node.text.replace('PART', '').strip()
        for node in reg_doc.xpath('//FDSYS/HEADING')
        if 'PART' in node.text)
    potential_parts.extend(
        # e-CFR XML, under FDSYS/GRANULENUM
        node.text.strip() for node in reg_doc.xpath('//FDSYS/GRANULENUM'))
    potential_parts = [p for p in potential_parts if p.strip()]

    if potential_parts:
        return potential_parts[0]


def get_title(reg_doc):
    """ Extract the title of the regulation. """
    parent = reg_doc.xpath('//PART/HD')[0]
    title = parent.text
    return title


def preprocess_xml(xml):
    """This transforms the read XML through macros. Each macro consists of
    an xpath and a replacement xml string"""
    logger.info("Preprocessing XML %s", xml)
    for path, replacement in content.Macros():
        replacement = etree.fromstring('<ROOT>' + replacement + '</ROOT>')
        for node in xml.xpath(path):
            parent = node.getparent()
            idx = parent.index(node)
            parent.remove(node)
            for repl in replacement:
                parent.insert(idx, repl)
                idx += 1


def build_tree(reg_xml):
    logger.info("Build tree %s", reg_xml)
    preprocess_xml(reg_xml)

    reg_part = get_reg_part(reg_xml)
    title = get_title(reg_xml)

    tree = Node("", [], [reg_part], title)

    part = reg_xml.xpath('//PART')[0]

    # Build a list of SUBPARTs, then pull SUBJGRPs into that list:
    subpart_and_subjgrp_xmls = part.xpath('./SUBPART|./SUBJGRP')

    if len(subpart_and_subjgrp_xmls) > 0:
        subthings = []
        letter_list = []
        for subthing in subpart_and_subjgrp_xmls:
            if subthing.tag == "SUBPART":
                subthings.append(build_subpart(reg_part, subthing))
            elif subthing.tag == "SUBJGRP":
                built_subjgrp = build_subjgrp(reg_part, subthing, letter_list)
                letter_list.append(built_subjgrp.label[-1])
                subthings.append(built_subjgrp)

        tree.children = subthings
    else:
        section_xmls = [c for c in part.getchildren() if c.tag == 'SECTION']
        sections = []
        for section_xml in section_xmls:
            sections.extend(build_from_section(reg_part, section_xml))
        empty_part = reg_text.build_empty_part(reg_part)
        empty_part.children = sections
        tree.children = [empty_part]

    non_reg_sections = build_non_reg_text(reg_xml, reg_part)
    tree.children += non_reg_sections

    return tree


def get_subpart_group_title(subpart_xml):
    """Derive the title of a subpart or subject group"""
    hds = subpart_xml.xpath('./RESERVED|./HD')
    if hds:
        return tree_utils.get_node_text(hds[0])


def build_subpart(reg_part, subpart_xml):
    subpart_title = get_subpart_group_title(subpart_xml)
    subpart = reg_text.build_subpart(subpart_title, reg_part)

    sections = []
    for ch in subpart_xml.getchildren():
        if ch.tag == 'SECTION':
            sections.extend(build_from_section(reg_part, ch))

    subpart.children = sections
    return subpart


def build_subjgrp(reg_part, subjgrp_xml, letter_list):
    # This handles subjgrps that have been pulled out and injected into the
    # same level as subparts.
    subjgrp_title = get_subpart_group_title(subjgrp_xml)
    letter_list, subjgrp = reg_text.build_subjgrp(subjgrp_title, reg_part,
                                                  letter_list)

    sections = []
    for ch in subjgrp_xml.getchildren():
        if ch.tag == 'SECTION':
            sections.extend(build_from_section(reg_part, ch))

    subjgrp.children = sections
    return subjgrp
