from regparser.tree import reg_text
from regparser.tree.gpo_cfr.section import build_from_section
from regparser.tree.xml_parser import matchers, tree_utils


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


def build_subpart(cfr_part, xml):
    subpart_title = get_subpart_group_title(xml)
    subpart = reg_text.build_subpart(subpart_title, cfr_part)

    sections = []
    for ch in xml.xpath('./SECTION'):
        sections.extend(build_from_section(cfr_part, ch))

    subpart.children = sections
    return subpart


@matchers.match_tag('SUBPART')
def parse_subpart(parent, xml_node):
    subpart = build_subpart(parent.cfr_part, xml_node)
    parent.children.append(subpart)


class ParseSubjectGroup(matchers.Parser):
    """We use a class here as we want to carry around the letter_list in
    between parses"""
    def __init__(self):
        self.letter_list = []

    def matches(self, parent, xml_node):
        return xml_node.tag == 'SUBJGRP'

    def __call__(self, parent, xml_node):
        subjgrp = build_subjgrp(parent.cfr_part, xml_node, self.letter_list)
        self.letter_list.append(subjgrp.label[-1])
        parent.children.append(subjgrp)
