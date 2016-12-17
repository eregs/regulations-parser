from copy import deepcopy

from regparser.notice.amendments.utils import label_amdpar_from
from regparser.tree.gpo_cfr.section import build_from_section


def content_for_regtext(instruction_xml):
    """Return a chunk of XML (which serves as a unique key) and a think for
    parsing that XML as a section"""
    label_parts, amdpar = label_amdpar_from(instruction_xml)
    xml = find_section(amdpar)

    def parse_regtext():
        sections = build_from_section(label_parts[0], xml)
        if sections:
            return sections[0]

    return xml, parse_regtext


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
