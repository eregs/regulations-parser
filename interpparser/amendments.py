# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
from copy import deepcopy

from lxml import etree

from interpparser import gpo_cfr
from regparser.notice.amendments.utils import label_amdpar_from
from regparser.notice.util import spaces_then_remove
from regparser.tree.struct import Node


def content_for_interpretations(instruction_xml):
    """Return a chunk of XML (which serves as a unique key) and a think for
    parsing that XML as an interpretation"""
    label_parts, amdpar = label_amdpar_from(instruction_xml)
    if len(label_parts) > 0 and 'Interpretations' in label_parts[1]:
        xml = amdpar.getparent()
        return xml, functools.partial(parse_interp, label_parts[0], xml)


def parse_interp(cfr_part, xml):
    """Figure out which parts of the parent_xml are relevant to
    interpretations. Pass those on to interpretations.parse_from_xml and
    return the results"""
    parent_xml = standardize_interp_xml(xml)

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
            header.text = sectno.text + '—' + subject.text
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
    root = gpo_cfr.parse_from_xml(root, xml_nodes)
    if not root.children:
        return None
    else:
        return root


def standardize_interp_xml(xml):
    """We will assume a format of Supplement I header followed by HDs,
    STARS, and Ps, so move anything in an EXTRACT up a level"""
    xml = spaces_then_remove(deepcopy(xml), 'PRTPAGE')
    for extract in xml.xpath(".//EXTRACT|.//APPENDIX|.//SUBPART"):
        ex_parent = extract.getparent()
        idx = ex_parent.index(extract)
        for child in extract:
            ex_parent.insert(idx, child)
            idx += 1
        ex_parent.remove(extract)
    return xml
