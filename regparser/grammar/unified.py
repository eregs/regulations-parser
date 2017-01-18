# -*- coding: utf-8 -*-
"""Some common combinations"""
from pyparsing import (FollowedBy, LineEnd, Literal, OneOrMore, Optional,
                       SkipTo, Suppress, ZeroOrMore)

from regparser.grammar import atomic
from regparser.grammar.utils import Marker, QuickSearchable, keep_pos

period_section = Suppress(".") + atomic.section
part_section = atomic.part + period_section
marker_part_section = (
    keep_pos(atomic.section_marker).setResultsName("marker") +
    part_section)

depth6_p = atomic.em_roman_p | atomic.plaintext_level6_p
depth5_p = (
    (atomic.em_digit_p | atomic.plaintext_level5_p) +
    Optional(depth6_p))
depth4_p = atomic.upper_p + Optional(depth5_p)
depth3_p = atomic.roman_p + Optional(depth4_p)
depth2_p = atomic.digit_p + Optional(depth3_p)
depth1_p = atomic.lower_p + ~FollowedBy(atomic.upper_p) + Optional(depth2_p)
any_depth_p = QuickSearchable(
    depth1_p | depth2_p | depth3_p | depth4_p | depth5_p | depth6_p)

depth3_c = atomic.upper_c + Optional(atomic.em_digit_c)
depth2_c = atomic.roman_c + Optional(depth3_c)
depth1_c = atomic.digit_c + Optional(depth2_c)
any_a = atomic.upper_a | atomic.digit_a

section_comment = atomic.section + depth1_c

section_paragraph = QuickSearchable(atomic.section + depth1_p)

mps_paragraph = QuickSearchable(marker_part_section + Optional(depth1_p))
ps_paragraph = part_section + Optional(depth1_p)
part_section_paragraph = QuickSearchable(
    atomic.part + Suppress(".") + atomic.section + depth1_p)


m_section_paragraph = QuickSearchable(
    keep_pos(atomic.paragraph_marker).setResultsName("marker") +
    atomic.section +
    depth1_p)

marker_paragraph = QuickSearchable(
    keep_pos(
        atomic.paragraph_marker | atomic.paragraphs_marker
    ).setResultsName("marker") +
    depth1_p)


def appendix_section(match):
    """Appendices may have parenthetical paragraphs in its section number."""
    if match.appendix_digit:
        lst = list(match)
        pars = lst[lst.index(match.appendix_digit) + 1:]
        section = match.appendix_digit
        if pars:
            section += '(' + ')('.join(el for el in pars) + ')'
        return section
    else:
        return None


appendix_with_section = QuickSearchable(
    atomic.appendix +
    '-' +
    (atomic.appendix_digit +
     ZeroOrMore(atomic.lower_p | atomic.roman_p | atomic.digit_p |
                atomic.upper_p)).setParseAction(
                    appendix_section).setResultsName("appendix_section"),
    # optimization: encode the regex
    force_regex_str=r"[A-Z]+[0-9]*\b\s*-")

appendix_with_part = QuickSearchable(
    keep_pos(atomic.appendix_marker).setResultsName("marker") +
    atomic.appendix +
    Suppress(",") + Marker('part') +
    atomic.upper_roman_a +
    Optional(any_a) + Optional(any_a) + Optional(any_a))

marker_appendix = QuickSearchable(
    keep_pos(atomic.appendix_marker).setResultsName("marker") +
    (appendix_with_section | atomic.appendix))

marker_part = (
    keep_pos(atomic.part_marker).setResultsName("marker") +
    atomic.part)

marker_subpart = (
    keep_pos(atomic.subpart_marker).setResultsName("marker") +
    atomic.subpart)

marker_subpart_title = (
    keep_pos(atomic.subpart_marker).setResultsName("marker") +
    atomic.subpart +
    Optional(Suppress(Literal(u"—"))) +
    SkipTo(LineEnd()).setResultsName("subpart_title")
)

marker_comment = QuickSearchable(
    keep_pos(atomic.comment_marker).setResultsName("marker") +
    (section_comment | section_paragraph | ps_paragraph | mps_paragraph) +
    Optional(depth1_c)
)


def make_multiple(head, tail=None, wrap_tail=False):
    """We have a recurring need to parse citations which have a string of
    terms, e.g. section 11(a), (b)(4), and (5). This function is a shorthand
    for setting these elements up"""
    if tail is None:
        tail = head
    head = keep_pos(head).setResultsName("head")
    # We need to address just the matching text separately from the
    # conjunctive phrase
    tail = keep_pos(tail).setResultsName("match")
    tail = (atomic.conj_phrases + tail).setResultsName(
        "tail", listAllMatches=True)
    if wrap_tail:
        tail = Optional(Suppress('(')) + tail + Optional(Suppress(')'))
    return QuickSearchable(head + OneOrMore(tail))


_inner_non_comment = (
    any_depth_p |
    (part_section + Optional(depth1_p)) |
    (atomic.section + depth1_p) |
    appendix_with_section | marker_appendix)


multiple_non_comments = QuickSearchable(
    (atomic.paragraphs_marker | atomic.paragraph_marker |
     atomic.sections_marker | atomic.section_marker) +
    make_multiple(_inner_non_comment, wrap_tail=True))

multiple_section_paragraphs = make_multiple(
    head=section_paragraph, tail=_inner_non_comment)

multiple_period_sections = QuickSearchable(
    atomic.sections_marker +
    make_multiple(head=part_section, tail=period_section))

multiple_appendix_section = make_multiple(
    head=appendix_with_section,
    tail=_inner_non_comment, wrap_tail=True)

multiple_appendices = QuickSearchable(
    atomic.appendices_marker +
    make_multiple(atomic.appendix))

multiple_comments = QuickSearchable(
    (atomic.comments_marker | atomic.comment_marker) +
    make_multiple(
        head=(Optional(atomic.section_marker) + _inner_non_comment +
              Optional(depth1_c)),
        tail=(_inner_non_comment + Optional(depth1_c)) | depth1_c,
        wrap_tail=True))

# e.g. 12 CFR 1005
cfr = QuickSearchable(
    atomic.title + Suppress("CFR") + Optional(Marker("part")) + atomic.part
)
# e.g. 12 CFR 1005.10
cfr_p = QuickSearchable(
    cfr +
    Suppress('.') +
    atomic.section +
    Optional(depth1_p))

# e.g. 12 CFR 1005.10, 1006.21, and 1010.10
multiple_cfr_p = make_multiple(
    head=cfr_p,
    tail=atomic.part + Suppress('.') + atomic.section + Optional(depth1_p))

notice_cfr_p = (
    atomic.title +
    Suppress("CFR") +
    Optional(Suppress(atomic.part_marker | atomic.parts_marker)) +
    OneOrMore(
        atomic.part.copy().setResultsName('cfr_parts', listAllMatches=True) +
        Optional(Suppress(',')) +
        Optional(Suppress('and'))
    )
)
