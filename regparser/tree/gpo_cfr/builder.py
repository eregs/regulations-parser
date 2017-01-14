# -*- coding: utf-8 -*-
import logging

from lxml import etree

from regparser import content, plugins
from regparser.tree.struct import Node

logger = logging.getLogger(__name__)


part_finders = []


def part_finder(xpath):
    """Decorator which will add a new entry to the part_finders list. Each
    decorated function should take an XML element and yield a string (or
    nothing)"""
    def wrapped(fn):
        part_finders.append((xpath, fn))
        return fn
    return wrapped


@part_finder('REGTEXT')
def fr_notice(xml_el):
    return xml_el.attrib['PART']


@part_finder('PART/EAR')
def annual1(xml_el):
    if 'Pt.' in xml_el.text:
        return xml_el.text.replace('Pt.', '').strip()


@part_finder('FDSYS/HEADING')
def annual2(xml_el):
    if 'PART' in xml_el.text:
        return xml_el.text.replace('PART', '').strip()


@part_finder('FDSYS/GRANULENUM')
def annual3(xml_el):
    return xml_el.text.strip()


def get_reg_part(reg_doc):
    """Depending on source, the CFR part number exists in different places.
    Fetch it, wherever it is."""
    potentials = [
        fn(xml_el)
        for xpath, fn in part_finders
        for xml_el in reg_doc.xpath('self::{0}|.//{0}'.format(xpath))
        if fn(xml_el)
    ]
    if potentials:
        return potentials[0]


def get_title(reg_doc):
    """ Extract the title of the regulation. """
    parent = reg_doc.xpath('self::PART/HD|.//PART/HD')[0]
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

    part = reg_xml.xpath('self::PART|.//PART')[0]
    matchers = list(plugins.instantiate_if_possible(
        'eregs_ns.parser.xml_matchers.gpo_cfr.PART'))

    for xml_node in part.getchildren():
        for plugin in matchers:
            if plugin.matches(tree, xml_node):
                plugin(tree, xml_node)

    return tree
