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
    def transform(self, xml):
        for amdpar in xml.xpath("//AMDPAR"):
            if amdpar.getnext() is None:
                parent = amdpar.getparent()
                next_parent = parent.getnext()
                if (next_parent is not None
                        and parent.get('PART') == next_parent.get('PART')):
                    parent.remove(amdpar)
                    next_parent.insert(0, amdpar)


class SupplementIAMDPar(PreProcessorBase):
    """Supplement I AMDPARs are often incorrect (labelled as Ps)"""
    def transform(self, xml):
        xpath_contains_supp = "contains(., 'Supplement I')"
        xpath = "//REGTEXT//HD[@SOURCE='HD1' and %s]" % xpath_contains_supp
        for supp_header in xml.xpath(xpath):
            parent = supp_header.getparent()
            if (parent.xpath("./AMDPAR[%s]" % xpath_contains_supp)
                    or parent.xpath("./P[%s]" % xpath_contains_supp)):
                pred = supp_header.getprevious()
                while pred is not None:
                    if pred.tag not in ('P', 'AMDPAR'):
                        pred = pred.getprevious()
                    else:
                        pred.tag = 'AMDPAR'
                        if 'supplement i' in pred.text.lower():
                            pred = None
                        else:
                            pred = pred.getprevious()


class EmphasizedParagraphCleanup(PreProcessorBase):
    """Clean up emphasized paragraph tags"""
    def transform(self, xml):
        for par in xml.xpath("//P/*[position()=1 and name()='E']/.."):
            em = par.getchildren()[0]   # must be an E from the xpath

            #   wrap in a thunk to delay execution
            par_text = lambda: par.text or ""
            em_text, em_tail = lambda: em.text or "", lambda: em.tail or ""

            par_open = par_text()[-1:] == "("
            em_open = em_text()[:1] == "("
            em_txt_closed = em_text()[-1:] == ")"
            em_tail_closed = em_tail()[:1] == ")"

            if (par_open or em_open) and (em_txt_closed or em_tail_closed):
                if not par_open and em_open:                # Move '(' out
                    par.text = par_text() + "("
                    em.text = em_text()[1:]

                if not em_tail_closed and em_txt_closed:    # Move ')' out
                    em.text = em_text()[:-1]
                    em.tail = ")" + em_tail()


# Surface all of the PreProcessorBase classes
ALL = PreProcessorBase.__subclasses__()
