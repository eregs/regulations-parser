"""Set of transforms we run on notice XML to account for common inaccuracies
in the XML"""
import abc
import re

from lxml import etree


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
        _str = lambda x: x or ""
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
    def extract_pair(self, extract):
        """Checks for and merges two EXTRACT tags in sequence"""
        next_el = extract.getnext()
        if next_el is not None and next_el.tag == 'EXTRACT':
            self.combine_with_following(extract, include_tag=False)
            return True
        return False

    def sandwich(self, extract):
        """Checks for this pattern: EXTRACT (FTNT|GPOTABLE) EXTRACT, and, if
        present, combines the first two tags. The two EXTRACTs would get
        merged in a later pass"""
        next_el = extract.getnext()
        next_next_el = next_el is not None and next_el.getnext()
        if next_el is not None and next_next_el is not None:
            has_filling = next_el.tag in ('FTNT', 'GPOTABLE')
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


# Surface all of the PreProcessorBase classes
ALL = PreProcessorBase.__subclasses__()
