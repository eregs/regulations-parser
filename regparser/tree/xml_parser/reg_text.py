# vim: set encoding=utf-8
import re

from lxml import etree

from regparser import content
from regparser.grammar.unified import any_depth_p
from regparser.tree import reg_text
from regparser.tree.depth import markers as mtypes, optional_rules
from regparser.tree.struct import Node
from regparser.tree.paragraph import p_level_of, p_levels
from regparser.tree.xml_parser import (
    flatsubtree_processor, import_category, paragraph_processor,
    simple_hierarchy_processor, tree_utils)
from regparser.tree.xml_parser.appendices import build_non_reg_text


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
    preprocess_xml(reg_xml)

    reg_part = get_reg_part(reg_xml)
    title = get_title(reg_xml)

    tree = Node("", [], [reg_part], title)

    part = reg_xml.xpath('//PART')[0]

    # Build a list of SUBPARTs, then pull SUBJGRPs into that list:
    subpart_and_subjgrp_xmls = []
    for subpart in part.xpath('./SUBPART|./SUBJGRP'):
        subpart_and_subjgrp_xmls.append(subpart)
        # SUBJGRPS can be nested, particularly inside SUBPARTs
        for subjgrp in subpart.xpath('./SUBJGRP'):
            subpart_and_subjgrp_xmls.append(subjgrp)

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


def get_subpart_title(subpart_xml):
    hds = subpart_xml.xpath('./RESERVED|./HD')
    if hds:
        return [hd.text for hd in hds][0]


def get_subjgrp_title(subjgrp_xml):
    hds = subjgrp_xml.xpath('./RESERVED|./HD')
    if hds:
        return [hd.text for hd in hds][0]


def build_subpart(reg_part, subpart_xml):
    subpart_title = get_subpart_title(subpart_xml)
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
    subjgrp_title = get_subjgrp_title(subjgrp_xml)
    letter_list, subjgrp = reg_text.build_subjgrp(subjgrp_title, reg_part,
                                                  letter_list)

    sections = []
    for ch in subjgrp_xml.getchildren():
        if ch.tag == 'SECTION':
            sections.extend(build_from_section(reg_part, ch))

    subjgrp.children = sections
    return subjgrp


def _deeper_level(first, second):
    """Is the second marker deeper than the first"""
    for level1 in p_level_of(first):
        for level2 in p_level_of(second):
            if level1 < level2:
                return True
    return False


def _continues_collapsed(first, second):
    """Does the second marker continue a sequence started by the first?"""
    if second == mtypes.STARS_TAG:  # Missing data - proceed optimistically
        return True
    for level1, markers1 in enumerate(p_levels):
        for level2, markers2 in enumerate(p_levels):
            if first not in markers1 or second not in markers2:
                continue
            idx1, idx2 = markers1.index(first), markers2.index(second)
            extending = level1 == level2 and idx2 == idx1 + 1
            new_level = level2 == level1 + 1 and idx2 == 0
            if extending or new_level:
                return True
    return False


def get_markers(text, next_marker=None):
    """ Extract all the paragraph markers from text. Do some checks on the
    collapsed markers."""
    initial = initial_markers(text)
    if next_marker is None:
        collapsed = []
    else:
        collapsed = tree_utils.get_collapsed_markers(text)

    #   Check that the collapsed markers make sense:
    #   * at least one level below the initial marker
    #   * followed by a marker in sequence
    if initial and collapsed:
        collapsed = [c for c in collapsed if _deeper_level(initial[-1], c)]
        for marker in reversed(collapsed):
            if _continues_collapsed(marker, next_marker):
                break
            else:
                collapsed.pop()

    return initial + collapsed


def initial_markers(text):
    """Pull out a list of the first paragraph markers, i.e. markers before any
    text"""
    for citation, start, end in any_depth_p.scanString(text):
        if start == 0:
            markers = [citation.p1, citation.p2, citation.p3, citation.p4,
                       citation.p5, citation.p6]
            if markers[4]:
                markers[4] = '<E T="03">' + markers[4] + '</E>'
            if markers[5]:
                markers[5] = '<E T="03">' + markers[5] + '</E>'
            return list(filter(bool, markers))
    return []


def get_markers_and_text(node, markers_list):
    node_text = tree_utils.get_node_text(node, add_spaces=True)
    text_with_tags = tree_utils.get_node_text_tags_preserved(node)

    actual_markers = ['(%s)' % m for m in markers_list]
    plain_markers = [m.replace('<E T="03">', '').replace('</E>', '')
                     for m in actual_markers]
    node_texts = tree_utils.split_text(node_text, plain_markers)
    tagged_texts = tree_utils.split_text(text_with_tags, actual_markers)
    node_text_list = zip(node_texts, tagged_texts)

    if len(node_text_list) > len(markers_list):     # diff can only be 1
        markers_list.insert(0, mtypes.MARKERLESS)
    return zip(markers_list, node_text_list)


def build_from_section(reg_part, section_xml):
    section_no = section_xml.xpath('SECTNO')[0].text
    subject_xml = section_xml.xpath('SUBJECT')
    if not subject_xml:
        subject_xml = section_xml.xpath('RESERVED')
    subject_text = (subject_xml[0].text or '').strip()

    section_nums = []
    for match in re.finditer(r'%s\.(\d+[a-z]*)' % reg_part, section_no):
        secnum_candidate = match.group(1)
        if secnum_candidate.isdigit():
            secnum_candidate = int(secnum_candidate)
        section_nums.append(secnum_candidate)

    #  Span of section numbers
    if u'§§' == section_no[:2] and '-' in section_no:
        first, last = section_nums
        section_nums = []
        for i in range(first, last + 1):
            section_nums.append(i)

    section_nodes = []
    for section_number in section_nums:
        section_number = str(section_number)
        section_text = section_xml.text.strip()
        tagged_section_text = section_xml.text

        section_title = u"§ " + reg_part + "." + section_number
        if subject_text:
            section_title += " " + subject_text

        sect_node = Node(
            section_text, label=[reg_part, section_number],
            title=section_title)
        sect_node.tagged_text = tagged_section_text

        section_nodes.append(
            RegtextParagraphProcessor().process(section_xml, sect_node)
        )
    return section_nodes


class ParagraphMatcher(paragraph_processor.BaseMatcher):
    """<P>/<FP> with or without initial paragraph markers -- (a)(1)(i) etc."""
    def matches(self, xml):
        return xml.tag in ('P', 'FP')

    def derive_nodes(self, xml, processor=None):
        text = ''
        tagged_text = tree_utils.get_node_text_tags_preserved(xml).strip()
        markers_list = get_markers(tagged_text, self.next_marker(xml))
        nodes = []
        for m, node_text in get_markers_and_text(xml, markers_list):
            text, tagged_text = node_text
            node = Node(text=text.strip(), label=[m], source_xml=xml)
            node.tagged_text = unicode(tagged_text.strip())
            nodes.append(node)
        if text.endswith('* * *'):
            nodes.append(Node(label=[mtypes.INLINE_STARS]))
        return nodes

    def next_marker(self, xml):
        """Find the first marker in a paragraph that follows this xml node.
        May return None"""
        good_tags = ('P', 'FP', mtypes.STARS_TAG)

        node = xml.getnext()
        while node is not None and node.tag not in good_tags:
            node = node.getnext()

        if getattr(node, 'tag', None) == mtypes.STARS_TAG:
            return mtypes.STARS_TAG
        elif node is not None:
            tagged_text = tree_utils.get_node_text_tags_preserved(node)
            markers = get_markers(tagged_text.strip())
            if markers:
                return markers[0]


class RegtextParagraphProcessor(paragraph_processor.ParagraphProcessor):
    MATCHERS = [paragraph_processor.StarsMatcher(),
                paragraph_processor.TableMatcher(),
                paragraph_processor.FencedMatcher(),
                flatsubtree_processor.FlatsubtreeMatcher(
                    tags=['EXTRACT'], node_type=Node.EXTRACT),
                import_category.ImportCategoryMatcher(),
                flatsubtree_processor.FlatsubtreeMatcher(tags=['EXAMPLE']),
                paragraph_processor.HeaderMatcher(),
                ParagraphMatcher(),
                simple_hierarchy_processor.SimpleHierarchyMatcher(
                    tags=['NOTE', 'NOTES'], node_type=Node.NOTE)]

    def additional_constraints(self):
        return [optional_rules.depth_type_inverses,
                optional_rules.star_new_level,
                optional_rules.limit_sequence_gap(),
                optional_rules.limit_paragraph_types(
                    mtypes.lower, mtypes.upper, mtypes.ints, mtypes.roman,
                    mtypes.em_ints, mtypes.em_roman, mtypes.stars,
                    mtypes.markerless)]
