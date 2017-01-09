# -*- coding: utf-8 -*-
"""Set of transforms we run on notice XML to account for common inaccuracies
in the XML"""
from __future__ import unicode_literals

import abc
import functools
import logging
import re
from copy import deepcopy
from itertools import takewhile

import six
from lxml import etree
from six.moves.html_parser import HTMLParser

from regparser.grammar.tokens import uncertain_label
from regparser.notice.amdparser import parse_amdpar
from regparser.tree.xml_parser.tree_utils import (get_node_text,
                                                  replace_xml_node_with_text)

logger = logging.getLogger(__name__)


# Anything "&upTo12Chars;" that's not &quot; &amp; &apos; &lt; &gt;
# https://en.wikipedia.org/wiki/List_of_XML_and_HTML_character_entity_references#Predefined_entities_in_XML
HTML_RE = re.compile(b'&(?!(quot|amp|apos|lt|gt))[^;]{0,12};')


def replace_html_entities(xml_bin_str):
    """XML does not contain entity references for many HTML entities, yet the
    Federal Register XML sometimes contains the HTML entities. Replace them
    here, lest we throw off XML parsing"""
    parser = HTMLParser()
    match = HTML_RE.search(xml_bin_str)
    while match:
        match_bin = match.group(0)
        match_str = match_bin.decode('utf-8')
        replacement = parser.unescape(match_str).encode('UTF-8')
        logger.debug("Replacing %s with %s in retrieved XML",
                     match_str, replacement)
        xml_bin_str = xml_bin_str.replace(match_bin, replacement)
        match = HTML_RE.search(xml_bin_str)
    return xml_bin_str


class PreProcessorBase(six.with_metaclass(abc.ABCMeta)):
    """Base class for all the preprocessors. Defines the interface they must
    implement"""
    @abc.abstractmethod
    def transform(self, xml):
        """Transform the input xml. Mutates that xml, so be sure to make a
        copy if needed"""
        raise NotImplementedError()


_AMDPAR_WITHOUT_FOLLOWING = "//AMDPAR[not(following-sibling::*)]"


def move_last_amdpar(xml):
    """If the last element in a section is an AMDPAR, odds are the authors
    intended it to be associated with the following section"""
    # AMDPAR with no following node
    for amdpar in xml.xpath(_AMDPAR_WITHOUT_FOLLOWING):
        parent = amdpar.getparent()
        aunt = parent.getnext()
        if aunt is not None and parent.get('PART') == aunt.get('PART'):
            parent.remove(amdpar)
            aunt.insert(0, amdpar)


def parentheses_cleanup(xml):
    """Clean up where parentheses exist between paragraph an emphasis tags"""
    # We want to treat None's as blank strings
    def _str(x):
        return x or ""
    for em in xml.xpath("//P/*[position()=1 and name()='E']"):
        par = em.getparent()
        left, middle, right = _str(par.text), _str(em.text), _str(em.tail)
        has_open = '(' in left[-1:] + middle[:1]
        has_close = ')' in middle[-1:] + right[:1]

        if not left.endswith('(') and middle.startswith('(') and has_close:
            # Move '(' out
            par.text = _str(par.text) + "("
            em.text = em.text[1:]

        if middle.endswith(')') and not right.startswith(')') and has_open:
            # Move ')' out
            em.text = em.text[:-1]
            em.tail = ")" + _str(em.tail)


_ORPHAN_REGEX = re.compile(r"(\.|—)")


def move_adjoining_chars(xml):
    """If an e tag has an emdash or period after it, put the char inside the e
    tag"""
    for e in xml.xpath("//P/E"):
        orphan = _ORPHAN_REGEX.match(e.tail or '')

        if orphan:
            e.text = (e.text or '') + orphan.group(1)
            e.tail = _ORPHAN_REGEX.sub('', e.tail, 1)


class ApprovalsFP(PreProcessorBase):
    """We expect certain text to an APPRO tag, but it is often mistakenly
    found inside FP tags. We use REGEX to determine which nodes need to be
    fixed."""
    REGEX = re.compile(
        r"\(.*approved by the office of management and budget under control "
        r"number .*\)", re.IGNORECASE)

    def transform(self, xml):
        for fp in xml.xpath(".//FP"):
            if self.REGEX.match(fp.text or ""):
                fp.tag = 'APPRO'
        self.strip_extracts(xml)

    @staticmethod
    def strip_extracts(xml):
        """APPROs should not be alone in an EXTRACT"""
        for appro in xml.xpath(".//APPRO"):
            parent = appro.getparent()
            inside_extract = parent.tag == 'EXTRACT'
            no_prev = appro.getprevious() is None
            no_next = appro.getnext() is None
            if inside_extract and no_prev and no_next:
                grandparent = parent.getparent()
                idx = grandparent.index(parent)
                grandparent.remove(parent)
                grandparent.insert(idx, appro)


class ExtractTags(PreProcessorBase):
    """Often, what should be a single EXTRACT tag is broken up by incorrectly
    positioned subtags. Try to find any such EXTRACT sandwiches and merge."""
    FILLING = ('FTNT', 'GPOTABLE')  # tags which shouldn't be between EXTRACTs

    def extract_pair(self, extract):
        """Checks for and merges two EXTRACT tags in sequence"""
        next_el = extract.getnext()
        if next_el is not None and next_el.tag == 'EXTRACT':
            self.combine_with_following(extract, include_tag=False)
            return True
        return False

    def sandwich(self, extract):
        """Checks for this pattern: EXTRACT FILLING EXTRACT, and, if present,
        combines the first two tags. The two EXTRACTs would get merged in a
        later pass"""
        next_el = extract.getnext()
        next_next_el = next_el is not None and next_el.getnext()
        if next_el is not None and next_next_el is not None:
            has_filling = next_el.tag in self.FILLING
            has_bread = next_next_el.tag == 'EXTRACT'
            if has_filling and has_bread:   # -> is sandwich
                self.combine_with_following(extract, include_tag=True)
                return True
        return False

    @staticmethod
    def strip_root_tag(string):
        first_tag_ends_at = string.find('>')
        last_tag_starts_at = string.rfind('<')
        return string[first_tag_ends_at + 1:last_tag_starts_at]

    def combine_with_following(self, extract, include_tag):
        """We need to merge an extract with the following tag. Rather than
        iterating over the node, text, tail text, etc. we're taking a more
        naive solution: convert to a string, reparse"""
        next_el = extract.getnext()
        if next_el is not None:
            xml_str = self.strip_root_tag(etree.tounicode(extract))
            next_str = etree.tounicode(next_el)

            if include_tag:
                xml_str += '\n' + next_str
            else:
                xml_str += '\n' + self.strip_root_tag(next_str)

            new_el = etree.fromstring('<EXTRACT>{0}</EXTRACT>'.format(xml_str))

            parent = extract.getparent()
            parent.replace(extract, new_el)
            parent.remove(next_el)

    def transform(self, xml):
        # we're going to be mutating the tree while searching it, so we'll
        # reset after every find
        should_continue = True
        while should_continue:
            should_continue = False
            for extract in xml.xpath(".//EXTRACT"):
                if self.extract_pair(extract) or self.sandwich(extract):
                    should_continue = True
                    break


class Footnotes(PreProcessorBase):
    """The XML separates the content of footnotes and where they are
    referenced. To make it more semantic (and easier to process), we find the
    relevant footnote and attach its text to the references. We also need to
    split references apart if multiple footnotes apply to the same <SU>"""
    # SU indicates both the reference and the content of the footnote;
    # distinguish by looking at ancestors
    IS_REF_PREDICATE = 'not(ancestor::TNOTE) and not(ancestor::FTNT)'
    XPATH_IS_REF = './/SU[{0}]'.format(IS_REF_PREDICATE)
    # Find the content of a footnote to associate with a reference
    XPATH_FIND_NOTE_TPL = \
        "./following::SU[(ancestor::TNOTE or ancestor::FTNT) and text()='{0}']"

    def transform(self, xml):
        self.split_comma_footnotes(xml)
        self.add_ref_attributes(xml)

    def split_comma_footnotes(self, xml):
        """Convert XML such as <SU>1, 2, 3</SU> into distinct SU elements:
        <SU>1</SU> <SU>2</SU> <SU>3</SU> for easier reference"""
        for ref_xml in xml.xpath(self.XPATH_IS_REF):
            parent = ref_xml.getparent()
            idx_in_parent = parent.index(ref_xml)
            parent.remove(ref_xml)  # we will be replacing this shortly

            refs = [txt.strip() for txt in re.split(r'[,|\s]+', ref_xml.text)]
            tail_texts = self._tails_corresponding_to(ref_xml, refs)

            def strip_tail(s):
                """ We want any whitespace, or any comma surrounded by
                whitespace, to become an empty string; otherwise strip() and
                return the original. """
                if s.strip() == ",":
                    return ""
                else:
                    return s.strip()

            tail_texts = [strip_tail(tail) for tail in tail_texts]

            for idx, (ref, tail) in enumerate(zip(refs, tail_texts)):
                node = etree.Element("SU")
                node.text = ref
                node.tail = tail
                parent.insert(idx_in_parent + idx, node)

    @staticmethod
    def _tails_corresponding_to(su, refs):
        """Given an <SU> element and a list of texts it should be broken into,
        return a list of the "tail" texts, that is, the text which will be
        between <SU>s"""
        to_process = su.text

        tail_texts = []
        for ref in reversed(refs):
            idx = to_process.rfind(ref)
            tail_texts.append(to_process[idx + len(ref):])
            to_process = to_process[:idx]
        # The last (reversed first) tail should contain the su.tail
        tail_texts[0] += su.tail or ''

        return list(reversed(tail_texts))

    def add_ref_attributes(self, xml):
        """Modify each footnote reference so that it has an attribute
        containing its footnote content"""
        for ref in xml.xpath(self.XPATH_IS_REF):
            sus = ref.xpath(self.XPATH_FIND_NOTE_TPL.format(ref.text))
            if sus and self.is_reasonably_close(ref, sus[0]):
                # copy as we need to modify
                note = deepcopy(sus[0].getparent())

                # Modify note to remove the reference text; it's superfluous
                for su in note.xpath('./SU'):
                    replace_xml_node_with_text(su, su.tail or '')
                ref.attrib['footnote'] = get_node_text(note).strip()

    @staticmethod
    def is_reasonably_close(referencing, referenced):
        """We want to make sure that _potential_ footnotes are truly related,
        as SU might also indicate generic superscript. To match a footnote
        with its content, we'll try to find a common SECTION ancestor. We'll
        also consider the two SUs related if neither has a SECTION ancestor,
        though we might want to restrict this further in the future."""
        while referencing is not None and referencing.tag != 'SECTION':
            referencing = referencing.getparent()
        while referenced is not None and referenced.tag != 'SECTION':
            referenced = referenced.getparent()
        return referencing == referenced


# parent of any AMDPAR _without_ an EREGS_INSTRUCTIONS elt
_AMDPARENT_XPATH = '//AMDPAR[not(EREGS_INSTRUCTIONS)]/..'


def preprocess_amdpars(xml):
    """Modify the AMDPAR tag to contain an <EREGS_INSTRUCTIONS> element. This
    element contains an interpretation of the AMDPAR, as viewed as a sequence
    of actions for how to modify the CFR. Do _not_ modify any existing
    EREGS_INSTRUCTIONS (they've been manually created)"""
    has_part = xml.xpath('//*[AMDPAR and @PART]')
    context = ['0']
    if has_part:
        context = [has_part[0].get('PART')]
    elif xml.xpath('//AMDPAR'):
        logger.warning('Could not find any PART designators.')

    for amdparent in xml.xpath(_AMDPARENT_XPATH):
        # Always start with only the CFR part
        context = [amdparent.get('PART') or context[0]]
        for amdpar in amdparent.xpath('.//AMDPAR'):
            instructions, context = parse_amdpar(amdpar, context)
            amdpar.append(instructions)
            instructions.set('final_context', uncertain_label(context))


preprocess_amdpars.plugin_order = 10    # Must be after move_last_amdpar


_MARKER_50032 = (
    "//SECTNO[contains(., '478.103')]/.."     # In 478.103
    # Look for a P with the appropriate key words
    "/P[contains(., 'ATF I 5300.2') and contains(., 'shall state')]"
)


def atf_i50032(xml):
    """478.103 contains a chunk of text which is meant to appear in a poster
    and be easily copy-paste-able. Unfortunately, the XML post 2003 isn't
    structured to contain all of the appropriate elements within the EXTRACT
    associated with the poster. This PreProcessor moves these additional
    elements back into the appropriate EXTRACT."""
    for p in xml.xpath(_MARKER_50032):
        siblings = list(p.itersiblings())
        to_move = list(takewhile(lambda s: s.tag != 'EXTRACT', siblings))
        extracts = list(p.itersiblings('EXTRACT'))
        if extracts:
            # reversed as we're inserting into the beginning
            for xml_el in reversed(to_move):
                extracts[0].insert(0, xml_el)


_MARKER_50031 = (
    "//SECTNO[contains(., '478.103')]/.."     # In 478.103
    # Look for a P with the appropriate key words
    "/P[contains(., 'ATF I 5300.1') and contains(., 'shall state')]"
    # First following EXTRACT
    "/following-sibling::EXTRACT[1]"
)


def atf_i50031(xml):
    """478.103 also contains a shorter form, which appears in a smaller
    poster. Unfortunately, the XML didn't include the appropriate NOTE inside
    the corresponding EXTRACT"""
    for extract in xml.xpath(_MARKER_50031):
        next_el = extract.getnext()
        while next_el is not None and next_el.tag != 'P':
            extract.append(next_el)
            next_el = extract.getnext()


class ImportCategories(PreProcessorBase):
    """447.21 contains an import list, but the XML doesn't delineate the
    various categories well. We've created `IMPORTCATEGORY` tags to handle the
    hierarchy correctly, but we need to modify the XML to insert them in
    appropriate locations"""
    SECTION_HD = "//SECTNO[contains(., '447.21')]"
    CATEGORY_HD = ".//HD[contains(., 'categor')]"   # categor(y|ies)

    def transform(self, xml):
        for hd in xml.xpath(self.SECTION_HD):
            section = hd.getparent()
            self.remove_extract(section)
            category_headers = section.xpath(self.CATEGORY_HD)
            self.split_categories(category_headers)

    @staticmethod
    def remove_extract(section):
        """The XML currently (though this may change) contains a semantically
        meaningless EXTRACT. Remove it"""
        for extract in section.xpath('./EXTRACT'):
            parent = extract.getparent()
            idx = parent.index(extract)
            # reversed as we're inserting into the beginning
            for child in reversed(extract):
                parent.insert(idx, child)
            parent.remove(extract)

    @staticmethod
    def split_categories(category_headers):
        """We now have a big chunk of flat XML with headers and paragraphs.
        We'll make it semantic by converting these into bundles and wrapping
        them in IMPORTCATEGORY tags"""
        while category_headers:
            hd = category_headers[0]
            category_headers = category_headers[1:]

            category_el = etree.Element("IMPORTCATEGORY")
            parent = hd.getparent()
            parent.insert(parent.index(hd), category_el)

            iterator = hd
            while iterator is not None and iterator not in category_headers:
                next_el = iterator.getnext()
                category_el.append(iterator)
                iterator = next_el


def promote_nested_tags(tag, xml):
    """We don't currently support certain tags nested inside subparts, so
    promote each up one level"""
    # Reversed to account for the order of insertion
    for subjgrp_xml in reversed(xml.xpath('.//SUBPART/' + tag)):
        subpart_xml = subjgrp_xml.getparent()
        subpart_parent = subpart_xml.getparent()
        idx = subpart_parent.index(subpart_xml) + 1
        subpart_parent.insert(idx, subjgrp_xml)


promote_nested_subjgrp = functools.partial(promote_nested_tags, 'SUBJGRP')
promote_nested_appendix = functools.partial(promote_nested_tags, 'APPENDIX')
