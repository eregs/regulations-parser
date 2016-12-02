from regparser.commands import import_notice
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder


def test_has_requirments():
    """Validate that certain attributes are required"""
    root_attrs = {
        "eregs-version-id": "vvv",
        "fr-volume": 124,
        "fr-start-page": 44,
        "fr-end-page": 55
    }
    with XMLBuilder("ROOT", **root_attrs) as ctx:
        ctx.DATES(**{"eregs-published-date": "2005-05-05"})
    notice_xml = NoticeXML(ctx.xml_copy())
    assert import_notice.has_requirements(notice_xml)

    notice_xml = NoticeXML(ctx.xml_copy())
    del notice_xml.xml.attrib['eregs-version-id']
    assert not import_notice.has_requirements(notice_xml)

    notice_xml = NoticeXML(ctx.xml_copy())
    del notice_xml.xml.attrib['fr-volume']
    assert not import_notice.has_requirements(notice_xml)

    notice_xml = NoticeXML(ctx.xml_copy())
    del notice_xml.xml.attrib['fr-start-page']
    assert not import_notice.has_requirements(notice_xml)

    notice_xml = NoticeXML(ctx.xml_copy())
    del notice_xml.xml.xpath('//DATES')[0].attrib['eregs-published-date']
    assert not import_notice.has_requirements(notice_xml)
