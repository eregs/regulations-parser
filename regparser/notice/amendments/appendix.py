import functools
import logging
from copy import deepcopy
from itertools import dropwhile

from regparser.notice.amendments.utils import label_amdpar_from
from regparser.tree.gpo_cfr.appendices import process_appendix

logger = logging.getLogger(__name__)


def content_for_appendix(instruction_xml):
    """Return a chunk of XML (which serves as a unique key) and a think for
    parsing that XML as an appendix"""
    label_parts, amdpar = label_amdpar_from(instruction_xml)
    if len(label_parts) > 0 and 'Appendix' in label_parts[1]:
        xml = amdpar.getparent()
        letter = label_parts[1][len('Appendix:'):]
        return xml, functools.partial(parse_appendix, xml, label_parts[0],
                                      letter)


def parse_appendix(xml, cfr_part, letter):
    """Attempt to parse an appendix. Used when the entire appendix has been
    replaced/added or when we can use the section headers to determine our
    place. If the format isn't what we expect, display a warning."""
    xml = deepcopy(xml)
    hds = xml.xpath('//HD[contains(., "Appendix {0} to Part {1}")]'.format(
                    letter, cfr_part))
    if len(hds) == 0:
        logger.warning("Could not find Appendix %s to part %s",
                       letter, cfr_part)
    elif len(hds) > 1:
        logger.warning("Too many headers for %s to part %s",
                       letter, cfr_part)
    else:
        hd = hds[0]
        hd.set('SOURCE', 'HED')
        extract = hd.getnext()
        if extract is not None and extract.tag == 'EXTRACT':
            extract.insert(0, hd)
            for trailing in dropwhile(lambda n: n.tag != 'AMDPAR',
                                      extract.getchildren()):
                extract.remove(trailing)
            return process_appendix(extract, cfr_part)
        logger.warning("Bad format for whole appendix")
