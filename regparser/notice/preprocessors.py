"""Set of transforms we run on notice XML to account for common inaccuracies
in the XML"""
import abc


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


# Surface all of the PreProcessorBase classes
ALL = PreProcessorBase.__subclasses__()
