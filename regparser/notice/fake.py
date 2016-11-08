"""Generate a minimal notice without hitting the FR"""
from regparser.notice.xml import NoticeXML, TitlePartsRef

from lxml import etree


def build(doc_number, effective_on, cfr_title, cfr_part):
    notice_xml = NoticeXML(etree.fromstring("""
        <ROOT>
            <AGENCY></AGENCY>
            <SUBJECT></SUBJECT>
        </ROOT>
    """))
    notice_xml.fr_volume = 10
    notice_xml.version_id = doc_number
    notice_xml.effective = effective_on
    notice_xml.published = effective_on
    notice_xml.start_page = 0
    notice_xml.end_page = 0
    notice_xml.cfr_refs = [TitlePartsRef(cfr_title, [cfr_part])]
    return notice_xml
