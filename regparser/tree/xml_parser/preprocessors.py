# vim: set encoding=utf-8
"""Set of transforms we run on notice XML to account for common inaccuracies
in the XML"""
import abc
from copy import deepcopy
import re

from lxml import etree

from regparser.tree.xml_parser.tree_utils import (
    get_node_text, replace_xml_node_with_text)


class PreProcessorBase(object):
    """Base class for all the preprocessors. Defines the interface they must
    implement"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def transform(self, xml):
        """Transform the input xml. Mutates that xml, so be sure to make a
        copy if needed"""
        raise NotImplementedError()


class MoveLastAMDPar(PreProcessorBase):
    """If the last element in a section is an AMDPAR, odds are the authors
    intended it to be associated with the following section"""
    AMDPAR_WITHOUT_FOLLOWING = "//AMDPAR[not(following-sibling::*)]"

    def transform(self, xml):
        # AMDPAR with no following node
        for amdpar in xml.xpath(self.AMDPAR_WITHOUT_FOLLOWING):
            parent = amdpar.getparent()
            aunt = parent.getnext()
            if aunt is not None and parent.get('PART') == aunt.get('PART'):
                parent.remove(amdpar)
                aunt.insert(0, amdpar)


class SupplementAMDPar(PreProcessorBase):
    """Supplement I AMDPARs are often incorrect (labelled as Ps)"""
    CONTAINS_SUPPLEMENT = "contains(., 'Supplement I')"
    SUPPLEMENT_HD = "//REGTEXT//HD[@SOURCE='HD1' and {}]".format(
        CONTAINS_SUPPLEMENT)
    SUPPLEMENT_AMD_OR_P = "./AMDPAR[{0}]|./P[{0}]".format(
        CONTAINS_SUPPLEMENT)

    def transform(self, xml):
        for supp_header in xml.xpath(self.SUPPLEMENT_HD):
            parent = supp_header.getparent()
            if parent.xpath(self.SUPPLEMENT_AMD_OR_P):
                self.set_prev_to_amdpar(supp_header.getprevious())

    def set_prev_to_amdpar(self, xml_node):
        """Set the tag to AMDPAR on all previous siblings until we hit the
        Supplement I header"""
        if xml_node is not None and xml_node.tag in ('P', 'AMDPAR'):
            xml_node.tag = 'AMDPAR'
            if 'supplement i' not in xml_node.text.lower():     # not done
                self.set_prev_to_amdpar(xml_node.getprevious())
        elif xml_node is not None:
            self.set_prev_to_amdpar(xml_node.getprevious())


class ParenthesesCleanup(PreProcessorBase):
    """Clean up where parentheses exist between paragraph an emphasis tags"""
    def transform(self, xml):
        # We want to treat None's as blank strings
        def _str(x):
            return x or ""
        for par in xml.xpath("//P/*[position()=1 and name()='E']/.."):
            em = par.getchildren()[0]   # must be an E due to the xpath

            outside_open = _str(par.text).endswith("(")
            inside_open = _str(em.text).startswith("(")
            has_open = outside_open or inside_open

            inside_close = _str(em.text).endswith(")")
            outside_close = _str(em.tail).startswith(")")
            has_close = inside_close or outside_close

            if has_open and has_close:
                if not outside_open and inside_open:    # Move '(' out
                    par.text = _str(par.text) + "("
                    em.text = em.text[1:]

                if not outside_close and inside_close:  # Move ')' out
                    em.text = em.text[:-1]
                    em.tail = ")" + _str(em.tail)


class MoveAdjoiningChars(PreProcessorBase):
    ORPHAN_REGEX = re.compile(ur"(\.|—)")

    def transform(self, xml):
        # if an e tag has an emdash or period after it, put the
        # char inside the e tag
        for e in xml.xpath("//P/E"):
            orphan = self.ORPHAN_REGEX.match(e.tail or '')

            if orphan:
                e.text = e.text + orphan.group(1)
                e.tail = self.ORPHAN_REGEX.sub('', e.tail, 1)


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

    def strip_extracts(self, xml):
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

    def strip_root_tag(self, string):
        first_tag_ends_at = string.find('>')
        last_tag_starts_at = string.rfind('<')
        return string[first_tag_ends_at+1:last_tag_starts_at]

    def combine_with_following(self, extract, include_tag):
        """We need to merge an extract with the following tag. Rather than
        iterating over the node, text, tail text, etc. we're taking a more
        naive solution: convert to a string, reparse"""
        next_el = extract.getnext()
        if next_el is not None:
            xml_str = self.strip_root_tag(etree.tostring(extract))
            next_str = etree.tostring(next_el)

            if include_tag:
                xml_str += '\n' + next_str
            else:
                xml_str += '\n' + self.strip_root_tag(next_str)

            new_el = etree.fromstring('<EXTRACT>{}</EXTRACT>'.format(xml_str))

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
    XPATH_IS_REF = './/SU[{}]'.format(IS_REF_PREDICATE)
    # Find the content of a footnote to associate with a reference
    XPATH_FIND_NOTE_TPL = \
        "./following::SU[(ancestor::TNOTE or ancestor::FTNT) and text()='{}']"

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

    def _tails_corresponding_to(self, su, refs):
        """Given an <SU> element and a list of texts it should be broken into,
        return a list of the "tail" texts, that is, the text which will be
        between <SU>s"""
        to_process = su.text

        tail_texts = []
        for ref in reversed(refs):
            idx = to_process.rfind(ref)
            tail_texts.append(to_process[idx+len(ref):])
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


class AtfI50032(PreProcessorBase):
    """478.103 contains a chunk of text which is meant to appear in a poster
    and be easily copy-paste-able. Unfortunately, the XML post 2003 isn't
    structured to contain all of the appropriate elements within the EXTRACT
    associated with the poster. This PreProcessor moves these additional
    elements back into the appropriate EXTRACT."""
    MARKER = ("//SECTNO[contains(., '478.103')]/.."     # In 478.103
              # Look for a P with the appropriate key words
              "/P[contains(., 'ATF I 5300.2') and contains(., 'shall state')]")

    def transform(self, xml):
        for p in xml.xpath(self.MARKER):
            next_el = p.getnext()
            to_move = []
            while next_el is not None and next_el.tag != 'EXTRACT':
                to_move.append(next_el)
                next_el = next_el.getnext()
            if next_el is not None:
                extract = next_el
                # reversed as we're inserting into the beginning
                for xml_el in reversed(to_move):
                    extract.insert(0, xml_el)


class AtfI50031(PreProcessorBase):
    """478.103 also contains a shorter form, which appears in a smaller
    poster. Unfortunately, the XML didn't include the appropriate NOTE inside
    the corresponding EXTRACT"""
    MARKER = ("//SECTNO[contains(., '478.103')]/.."     # In 478.103
              # Look for a P with the appropriate key words
              "/P[contains(., 'ATF I 5300.1') and contains(., 'shall state')]"
              "/following-sibling::EXTRACT[1]")     # First following EXTRACT

    def transform(self, xml):
        for extract in xml.xpath(self.MARKER):
            next_el = extract.getnext()
            while next_el is not None and next_el.tag != 'P':
                extract.append(next_el)
                next_el = extract.getnext()


class USCode(PreProcessorBase):
    """478.103 contains a chunk of the US Code, but does not delineate it
    clearly from the rest of the text of the containing poster. We've created
    `USCODE` tags to clear up this confusion, but we need to modify the XML to
    insert them in the appropriate spot"""
    MARKER = ("//SECTNO[contains(., '478.103')]/.."     # In 478.103
              "//HD[contains(., '18 U.S.C.')]")  # US Code header

    def transform(self, xml):
        for hd in xml.xpath(self.MARKER):
            uscode = etree.Element("USCODE")
            next_el = hd.getnext()
            while next_el is not None and next_el.tag != 'HD':
                uscode.append(next_el)
                next_el = hd.getnext()

            hd_parent = hd.getparent()
            hd_idx = hd_parent.index(hd)
            hd_parent.insert(hd_idx + 1, uscode)


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

    def remove_extract(self, section):
        """The XML currently (though this may change) contains a semantically
        meaningless EXTRACT. Remove it"""
        for extract in section.xpath('./EXTRACT'):
            parent = extract.getparent()
            idx = parent.index(extract)
            # reversed as we're inserting into the beginning
            for child in reversed(extract):
                parent.insert(idx, child)
            parent.remove(extract)

    def split_categories(self, category_headers):
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


# Surface all of the PreProcessorBase classes
ALL = PreProcessorBase.__subclasses__()
