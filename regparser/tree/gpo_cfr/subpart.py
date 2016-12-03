from regparser.tree import reg_text
from regparser.tree.gpo_cfr.section import build_from_section
from regparser.tree.xml_parser import tree_utils


def get_subpart_group_title(subpart_xml):
    """Derive the title of a subpart or subject group"""
    hds = subpart_xml.xpath('./RESERVED|./HD')
    if hds:
        return tree_utils.get_node_text(hds[0])


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


def build_subpart(reg_part, subpart_xml):
    subpart_title = get_subpart_group_title(subpart_xml)
    subpart = reg_text.build_subpart(subpart_title, reg_part)

    sections = []
    for ch in subpart_xml.getchildren():
        if ch.tag == 'SECTION':
            sections.extend(build_from_section(reg_part, ch))

    subpart.children = sections
    return subpart
