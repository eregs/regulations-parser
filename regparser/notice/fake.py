"""Generate a minimal notice without hitting the FR"""


def build(doc_number, effective_on, cfr_title, cfr_part):
    return {
        "document_number": doc_number,
        "effective_on": effective_on,
        "initial_effective_on": effective_on,
        "publication_date": effective_on,
        "cfr_title": cfr_title,
        "cfr_parts": [str(cfr_part)],   # for consistency w/ normal notices
        "fr_url": None
    }


def effective_date_for(xml_tree):
    """Return the date associated with an annual edition of regulation XML"""
    nodes = xml_tree.xpath('//DATE') or xml_tree.xpath('//ORIGINALDATE')
    return nodes[0].text
