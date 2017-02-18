import functools

from regparser.notice.amendments.utils import label_amdpar_from
from regparser.notice.changes import Change
from regparser.tree.gpo_cfr.subpart import build_subpart


def content_for_new_subpart(instruction_xml):
    """Return a chunk of XML (which serves as a unique key) and a think for
    parsing that XML as a subpart"""
    label_parts, amdpar = label_amdpar_from(instruction_xml)
    if (instruction_xml.tag == 'POST' and len(label_parts) == 2
            and 'Subpart:' in label_parts[1]):
        xml = find_subpart(amdpar)
        return xml, functools.partial(build_subpart, label_parts[0], xml)


def find_subpart(amdpar_tag):
    """ Look amongst an amdpar tag's siblings to find a subpart. """
    for sibling in amdpar_tag.itersiblings():
        if sibling.tag == 'SUBPART':
            return sibling


def process_designate_subpart(amendment):
    """ Process the designate amendment if it adds a subpart. """
    label_id = '-'.join(amendment.label)
    return Change(label_id, {'action': 'DESIGNATE',
                             'destination': amendment.destination})
