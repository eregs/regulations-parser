# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import string

from regparser.grammar.unified import marker_subpart_title
from regparser.search import find_offsets, find_start, segments
from regparser.tree import struct
from regparser.tree.appendix.carving import find_appendix_start
from regparser.tree.supplement import find_supplement_start


def build_empty_part(part):
    """ When a regulation doesn't have a subpart, we give it an emptypart (a
    dummy subpart) so that the regulation tree is consistent. """

    label = [str(part), 'Subpart']
    return struct.Node(
        '', [], label, '', node_type=struct.Node.EMPTYPART)


def build_subpart(text, part):
    results = marker_subpart_title.parseString(text)
    subpart_letter = results.subpart
    subpart_title = results.subpart_title
    label = [str(part), 'Subpart', subpart_letter]

    return struct.Node(
        "", [], label, subpart_title, node_type=struct.Node.SUBPART)


def subjgrp_label(starting_title, letter_list):
    words = starting_title.split()
    candidate_title = ""
    suffixes = [""] + list(string.ascii_lowercase)
    if len(words) == 1:
        # E.g. if the word is "Penalties" the progression is:
        #
        # Pe    Pe.     Pen     Pen.    Pena    Pena.   <etc.>
        # Penalties.    Penalties-b.    Penalties-c.    <etc.>
        word = words[0]
        terminator = ""
        suffix_pos = 0
        pos = min([2, len(word)])
        while candidate_title == "" or candidate_title in letter_list:
            suffix = '-{0}'.format(suffixes[suffix_pos]) if suffix_pos else ''
            candidate_title = '{0}{1}{2}'.format(word[:pos], terminator,
                                                 suffix)

            if terminator:
                terminator = ""
                if pos < len(word):
                    pos = pos + 1
                else:
                    suffix_pos = suffix_pos + 1
            else:
                terminator = "."

        return candidate_title
    else:
        # E.g. if the title is "Change of Ownership" the progression is:
        #
        # CoO   C.o.O.  C_o_O   ChofOw  Ch.of.Ow.   <etc.>
        # ChangeofOwnership-a
        separators = ("", ".", "_")
        separator_pos, suffix_pos = 0, 0
        num_letters = 1
        longest = max(len(word) for word in words)
        while candidate_title == "" or candidate_title in letter_list:
            sep = separators[separator_pos]
            suffix = suffixes[suffix_pos]
            suffix = "-{0}".format(suffix) if suffix else ""
            suffix = "{0}{1}".format(sep, suffix) if sep == "." else suffix
            candidate_title = "{0}{1}".format(sep.join(
                word[:num_letters] for word in words), suffix)
            if separator_pos + 1 < len(separators):
                separator_pos = separator_pos + 1
            elif num_letters == longest:
                separator_pos = 0
                suffix_pos = suffix_pos + 1
            else:
                separator_pos = 0
                num_letters = num_letters + 1
        return candidate_title


def build_subjgrp(title, part, letter_list):
    """
    We're constructing a fake "letter" here by taking the first letter of each
    word in the subjgrp's title, or using the first two letters of the first
    word if there's just one—we're avoiding single letters to make sure we
    don't duplicate an existing subpart, and we're hoping that the initialisms
    created by this method are unique for this regulation.
    We can make this more robust by accepting a list of existing initialisms
    and returning both that list and the Node, and checking against the list
    as we construct them.
    """
    letter_title = subjgrp_label(title, letter_list)
    letter_list.append(letter_title)

    label = [str(part), 'Subjgrp', letter_title]

    return (letter_list, struct.Node(label=label, title=title,
                                     node_type=struct.Node.SUBPART))


def find_next_subpart_start(text):
    """ Find the start of the next Subpart (e.g. Subpart B)"""
    return find_start(text, 'Subpart', r'[A-Z]—')


def find_next_section_start(text, part):
    """Find the start of the next section (e.g. 205.14)"""
    return find_start(text, "§", str(part) + r"\.\d+")


def next_section_offsets(text, part):
    """Find the start/end of the next section"""
    offsets = find_offsets(text, lambda t: find_next_section_start(t, part))
    if offsets is None:
        return None

    start, end = offsets
    subpart_start = find_next_subpart_start(text)
    appendix_start = find_appendix_start(text)
    supplement_start = find_supplement_start(text)
    if subpart_start is not None \
            and subpart_start > start and subpart_start < end:
        end = subpart_start
    elif appendix_start is not None and appendix_start < end:
        end = appendix_start
    elif supplement_start is not None and supplement_start < end:
        end = supplement_start

    if end >= start:
        return (start, end)


def next_subpart_offsets(text):
    """Find the start,end of the next subpart"""
    offsets = find_offsets(text, find_next_subpart_start)
    if offsets is None:
        return None
    start, end = offsets
    appendix_start = find_appendix_start(text)
    supplement_start = find_supplement_start(text)
    if appendix_start is not None and appendix_start < end:
        end = appendix_start
    elif supplement_start is not None and supplement_start < end:
        end = supplement_start

    if end >= start:
        return (start, end)


def sections(text, part):
    """Return a list of section offsets. Does not include appendices."""
    def offsets_fn(remaining_text, idx, excludes):
        return next_section_offsets(remaining_text, part)
    return segments(text, offsets_fn)


def subparts(text):
    """ Return a list of subpart offset. Does not include appendices,
    supplements. """

    def offsets_fn(remaining_text, idx, excludes):
        return next_subpart_offsets(remaining_text)
    return segments(text, offsets_fn)
