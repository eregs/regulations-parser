from interpparser.gpo_cfr import get_app_title

_CONTAINS_SUPPLEMENT = "contains(., 'Supplement I')"
_SUPPLEMENT_HD = "//REGTEXT//HD[@SOURCE='HD1' and {0}]".format(
    _CONTAINS_SUPPLEMENT)
_SUPPLEMENT_AMD_OR_P = "./AMDPAR[{0}]|./P[{0}]".format(_CONTAINS_SUPPLEMENT)


def _set_prev_to_amdpar(xml_node):
    """Set the tag to AMDPAR on all previous siblings until we hit the
    Supplement I header"""
    if xml_node is not None and xml_node.tag in ('P', 'AMDPAR'):
        xml_node.tag = 'AMDPAR'
        if 'supplement i' not in xml_node.text.lower():     # not done
            _set_prev_to_amdpar(xml_node.getprevious())
    elif xml_node is not None:
        _set_prev_to_amdpar(xml_node.getprevious())


def supplement_amdpar(xml):
    """Supplement I AMDPARs are often incorrect (labelled as Ps)"""
    for supp_header in xml.xpath(_SUPPLEMENT_HD):
        parent = supp_header.getparent()
        if parent.xpath(_SUPPLEMENT_AMD_OR_P):
            _set_prev_to_amdpar(supp_header.getprevious())


def appendix_to_interp(xml):
    """Convert Supplement I APPENDIX tags to INTERP"""
    for appendix in xml.xpath('.//APPENDIX'):
        section_title = get_app_title(appendix)
        if 'Supplement' in section_title and 'Part' in section_title:
            appendix.tag = 'INTERP'
