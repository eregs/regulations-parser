from __future__ import unicode_literals

from datetime import date

import pytest
from mock import Mock

from regparser.history.delays import FRDelay
from regparser.notice import xml as notice_xml
from regparser.regs_gov import RegsGovDoc
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.web.settings import parser as settings


@pytest.fixture
def tmp_xml_paths(tmpdir):
    """Creates two tmpdirs, modifies settings.LOCAL_XML_PATHS and reverts"""
    dir1 = tmpdir.mkdir('dir1')
    dir2 = tmpdir.mkdir('dir2')
    original = settings.LOCAL_XML_PATHS
    settings.LOCAL_XML_PATHS = [str(dir1), str(dir2)]
    yield dir1, dir2
    settings.LOCAL_XML_PATHS = original


def test_empty(tmp_xml_paths):
    """If no copy is present, we get an empty list"""
    url = 'http://example.com/some/url'
    assert notice_xml.local_copies(url) == []

    tmp_xml_paths[0].mkdir('some')
    assert notice_xml.local_copies(url) == []


def test_order(tmp_xml_paths):
    """The first source will override the second"""
    url = 'http://example.com/some/url'
    paths = []
    for d in tmp_xml_paths:
        d.mkdir('some')
        paths.append(d.join('some', 'url'))

    paths[1].write('aaaaa')
    assert [str(paths[1])] == notice_xml.local_copies(url)

    paths[0].write('bbbbb')
    assert [str(paths[0])] == notice_xml.local_copies(url)


def test_splits(tmp_xml_paths):
    """If multiple files are present from a single source, return all"""
    url = 'http://example.com/xml/503.xml'
    dir1, _ = tmp_xml_paths
    dir1.mkdir('xml')
    paths = []
    for i in range(3):
        path = dir1.join('xml', '503-{0}.xml'.format(i + 1))
        paths.append(str(path))
        path.write(str(i) * 10)

    assert set(paths) == set(notice_xml.local_copies(url))


def _dummy_notice():
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Some content")
        ctx.PRTPAGE(P="455")
    return notice_xml.NoticeXML(ctx.xml)


def test_set_meta_data():
    """Several pieces of meta data should be set within the XML. We test that
    the NoticeXML wrapper can retrieve them and that, if we re-read the XML,
    they can still be pulled out"""
    xml = _dummy_notice()

    xml.effective = '2005-05-05'
    xml.published = '2004-04-04'
    xml.fr_volume = 22

    assert xml.effective == date(2005, 5, 5)
    assert xml.published == date(2004, 4, 4)
    assert xml.fr_volume == 22

    xml = notice_xml.NoticeXML(xml.xml)
    assert xml.effective == date(2005, 5, 5)
    assert xml.published == date(2004, 4, 4)
    assert xml.fr_volume == 22


def test_set_effective_date_create():
    """The DATES tag should get created if not present in the XML"""
    xml = _dummy_notice()

    xml.effective = '2005-05-05'
    assert xml.effective == date(2005, 5, 5)
    xml = notice_xml.NoticeXML(xml.xml)
    assert xml.effective == date(2005, 5, 5)


def test_derive_effective_date():
    """Effective date can be derived from the dates strings. When it is
    derived, it should also be set on the notice xml"""
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Effective on May 4, 2004")
    xml = notice_xml.NoticeXML(ctx.xml)

    xml.effective = '2002-02-02'
    assert xml.derive_effective_date() == date(2004, 5, 4)
    # does _not_ set that date
    assert xml.effective == date(2002, 2, 2)
    xml.effective = xml.derive_effective_date()
    assert xml.effective == date(2004, 5, 4)


def test_delays():
    """The XML should be search for any delaying text"""
    with XMLBuilder("ROOT") as ctx:
        with ctx.EFFDATE():
            ctx.P("The effective date of 11 FR 100 has been delayed until "
                  "April 1, 2010. The effective date of 11 FR 200 has also "
                  "been delayed until October 10, 2010")
    xml = notice_xml.NoticeXML(ctx.xml)

    assert xml.delays() == [FRDelay(11, 100, date(2010, 4, 1)),
                            FRDelay(11, 200, date(2010, 10, 10))]


def test_delays_empty_p():
    """Delaying text may have an empty P tag"""
    with XMLBuilder("ROOT") as ctx:
        with ctx.EFFDATE():
            ctx.P()
            ctx.P("The effective date of 11 FR 100 has been delayed until "
                  "April 1, 2010.")
    xml = notice_xml.NoticeXML(ctx.xml)

    assert xml.delays() == [FRDelay(11, 100, date(2010, 4, 1))]


def test_set_agencies_simple():
    """ Test that we can properly derive agency info from the metadata or the
    XML itself, and that it's added to the XML.  """
    agencies_info = [{
        'name': 'Environmental Protection Agency',
        'parent_id': None,
        'raw_name': 'ENVIRONMENTAL PROTECTION AGENCY',
        'url': ('https://www.federalregister.gov/agencies/'
                'environmental-protection-agency'),
        'json_url': 'https://www.federalregister.gov/api/v1/agencies/145.json',
        'id': 145
    }]
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Effective on May 4, 2004")
    xml = notice_xml.NoticeXML(ctx.xml)
    xml.set_agencies(agencies=agencies_info)
    assert len(xml.xpath("//EREGS_AGENCIES")) == 1
    eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
    assert len(eregs_agencies.xpath("//EREGS_AGENCY")) == 1
    epa = eregs_agencies.xpath("//EREGS_AGENCY")[0]
    assert epa.attrib["name"] == "Environmental Protection Agency"
    assert epa.attrib["raw-name"] == "ENVIRONMENTAL PROTECTION AGENCY"
    assert epa.attrib["agency-id"] == "145"


def test_set_agencies_singlesub():
    """ Test that we can properly derive agency info from the metadata and add
    it to the XML if there is a subagency.  """
    agencies_info = [
        {
            'name': 'Justice Department',
            'parent_id': None,
            'url': ('https://www.federalregister.gov/agencies/'
                    'justice-department'),
            'raw_name': 'DEPARTMENT OF JUSTICE',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '268.json'),
            'id': 268
        },
        {
            'name': 'Alcohol, Tobacco, Firearms, and Explosives Bureau',
            'parent_id': 268,
            'url': ('https://www.federalregister.gov/agencies/'
                    'alcohol-tobacco-firearms-and-explosives-bureau'),
            'raw_name': ('Bureau of Alcohol, Tobacco, Firearms and '
                         'Explosives'),
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '19.json'),
            'id': 19
        }
    ]
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Effective on May 4, 2004")
    xml = notice_xml.NoticeXML(ctx.xml)
    xml.set_agencies(agencies=agencies_info)
    assert len(xml.xpath("//EREGS_AGENCIES")) == 1
    eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
    assert len(eregs_agencies.xpath("//EREGS_AGENCY")) == 1
    doj = eregs_agencies.xpath("//EREGS_AGENCY")[0]
    assert doj.attrib["name"] == "Justice Department"
    assert doj.attrib["raw-name"] == "DEPARTMENT OF JUSTICE"
    assert doj.attrib["agency-id"] == "268"
    assert len(doj.xpath("//EREGS_SUBAGENCY")) == 1
    atf = doj.xpath("//EREGS_SUBAGENCY")[0]
    assert atf.attrib["name"] == ("Alcohol, Tobacco, Firearms, and "
                                  "Explosives Bureau")
    assert atf.attrib["raw-name"] == ("Bureau of Alcohol, Tobacco, Firearms "
                                      "and Explosives")
    assert atf.attrib["agency-id"] == "19"


def test_set_agencies_unrelated():
    """ Test that we can properly derive agency info from the metadata and add
    it to the XML if there is an agency and a non-child subagency.  """
    agencies_info = [
        {
            'name': 'Treasury Department',
            'parent_id': None,
            'url': ('https://www.federalregister.gov/agencies/'
                    'treasury-department'),
            'raw_name': 'DEPARTMENT OF THE TREASURY',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '497.json'),
            'id': 497
        },
        {
            'name': 'Alcohol, Tobacco, Firearms, and Explosives Bureau',
            'parent_id': 268,
            'url': ('https://www.federalregister.gov/agencies/'
                    'alcohol-tobacco-firearms-and-explosives-bureau'),
            'raw_name': ('Bureau of Alcohol, Tobacco, Firearms and '
                         'Explosives'),
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '19.json'),
            'id': 19
        }
    ]
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Effective on May 4, 2004")
    xml = notice_xml.NoticeXML(ctx.xml)
    xml.set_agencies(agencies=agencies_info)
    assert len(xml.xpath("//EREGS_AGENCIES")) == 1
    eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
    assert len(eregs_agencies.xpath("//EREGS_AGENCY")) == 1
    treas = eregs_agencies.xpath("//EREGS_AGENCY")[0]
    assert treas.attrib["name"] == "Treasury Department"
    assert treas.attrib["raw-name"] == "DEPARTMENT OF THE TREASURY"
    assert treas.attrib["agency-id"] == "497"
    assert len(eregs_agencies.xpath("//EREGS_SUBAGENCY")) == 1
    atf = eregs_agencies.xpath("//EREGS_SUBAGENCY")[0]
    assert atf.attrib["name"] == ('Alcohol, Tobacco, Firearms, and '
                                  'Explosives Bureau')
    assert atf.attrib["raw-name"] == ("Bureau of Alcohol, Tobacco, Firearms "
                                      "and Explosives")
    assert atf.attrib["agency-id"] == "19"


def test_set_agencies_mixed():
    """ Test that we can properly derive agency info from the metadata and add
    it to the XML if we have a parent-child relationship and an unrelated
    agency.  """
    agencies_info = [
        {
            'name': 'Treasury Department',
            'parent_id': None,
            'url': ('https://www.federalregister.gov/agencies/'
                    'treasury-department'),
            'raw_name': 'DEPARTMENT OF THE TREASURY',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '497.json'),
            'id': 497
        },
        {
            'name': 'Alcohol, Tobacco, Firearms, and Explosives Bureau',
            'parent_id': 268,
            'url': ('https://www.federalregister.gov/agencies/'
                    'alcohol-tobacco-firearms-and-explosives-bureau'),
            'raw_name': ('Bureau of Alcohol, Tobacco, Firearms and '
                         'Explosives'),
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '19.json'),
            'id': 19
        },
        {
            'name': 'Justice Department',
            'parent_id': None,
            'url': ('https://www.federalregister.gov/agencies/'
                    'justice-department'),
            'raw_name': 'DEPARTMENT OF JUSTICE',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '268.json'),
            'id': 268
        }
    ]
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Effective on May 4, 2004")
    xml = notice_xml.NoticeXML(ctx.xml)
    xml.set_agencies(agencies=agencies_info)
    assert len(xml.xpath("//EREGS_AGENCIES")) == 1
    eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
    assert len(eregs_agencies.xpath("//EREGS_AGENCY")) == 2
    treas = eregs_agencies.xpath("//EREGS_AGENCY")[0]
    assert treas.attrib["name"] == "Treasury Department"
    assert treas.attrib["raw-name"] == "DEPARTMENT OF THE TREASURY"
    assert treas.attrib["agency-id"] == "497"
    doj = eregs_agencies.xpath("//EREGS_AGENCY")[1]
    assert doj.attrib["name"] == "Justice Department"
    assert doj.attrib["raw-name"] == "DEPARTMENT OF JUSTICE"
    assert doj.attrib["agency-id"] == "268"
    assert len(doj.xpath("//EREGS_SUBAGENCY")) == 1
    atf = doj.xpath("//EREGS_SUBAGENCY")[0]
    assert atf.attrib["name"] == ('Alcohol, Tobacco, Firearms, and '
                                  'Explosives Bureau')
    assert atf.attrib["raw-name"] == ("Bureau of Alcohol, Tobacco, Firearms "
                                      "and Explosives")
    assert atf.attrib["agency-id"] == "19"


def test_set_agencies_generations():
    """ Test that we can properly derive agency info from the metadata and add
    it to the XML if we have nested parent-child relationships.  """
    agencies_info = [
        {
            'name': 'ATF subagency',
            'parent_id': 19,
            'url': 'https://www.federalregister.gov/agencies/atf-subagency',
            'raw_name': 'SUBAGENCY OF ATF',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '100023.json'),
            'id': 100023
        },
        {
            'name': 'Alcohol, Tobacco, Firearms, and Explosives Bureau',
            'parent_id': 268,
            'url': ('https://www.federalregister.gov/agencies/'
                    'alcohol-tobacco-firearms-and-explosives-bureau'),
            'raw_name': 'Bureau of Alcohol, Tobacco, Firearms and Explosives',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '19.json'),
            'id': 19
        },
        {
            'name': 'Justice Department',
            'parent_id': None,
            'url': ('https://www.federalregister.gov/agencies/'
                    'justice-department'),
            'raw_name': 'DEPARTMENT OF JUSTICE',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '268.json'),
            'id': 268
        },
        {
            'name': 'ATF subsubagency',
            'parent_id': 100023,
            'url': 'https://www.federalregister.gov/agencies/atf-subsubagency',
            'raw_name': 'SUBSUBAGENCY OF ATF',
            'json_url': ('https://www.federalregister.gov/api/v1/agencies/'
                         '100072.json'),
            'id': 100072
        },
    ]
    with XMLBuilder("ROOT") as ctx:
        with ctx.DATES():
            ctx.P("Effective on May 4, 2004")
    xml = notice_xml.NoticeXML(ctx.xml)
    xml.set_agencies(agencies=agencies_info)
    assert len(xml.xpath("//EREGS_AGENCIES")) == 1
    eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
    assert len(eregs_agencies.xpath("//EREGS_AGENCY")) == 1
    doj = eregs_agencies.xpath("//EREGS_AGENCY")[0]
    assert doj.attrib["name"] == "Justice Department"
    assert doj.attrib["raw-name"] == "DEPARTMENT OF JUSTICE"
    assert doj.attrib["agency-id"] == "268"
    assert len(doj.xpath("//EREGS_SUBAGENCY")) == 3
    assert len(doj.xpath("EREGS_SUBAGENCY")) == 1
    atf = doj.xpath("//EREGS_SUBAGENCY")[0]
    assert atf.attrib["name"] == ('Alcohol, Tobacco, Firearms, and '
                                  'Explosives Bureau')
    assert atf.attrib["raw-name"] == ("Bureau of Alcohol, Tobacco, "
                                      "Firearms and Explosives")
    assert atf.attrib["agency-id"] == "19"
    assert len(atf.xpath("EREGS_SUBAGENCY")) == 1
    subatf = atf.xpath("EREGS_SUBAGENCY")[0]
    assert subatf.attrib["name"] == 'ATF subagency'
    assert subatf.attrib["raw-name"] == "SUBAGENCY OF ATF"
    assert subatf.attrib["agency-id"] == "100023"
    subsubatf = subatf.xpath("EREGS_SUBAGENCY")[0]
    assert subsubatf.attrib["name"] == 'ATF subsubagency'
    assert subsubatf.attrib["raw-name"] == "SUBSUBAGENCY OF ATF"
    assert subsubatf.attrib["agency-id"] == "100072"


@pytest.mark.parametrize('rins,expected,xml_rins', (
    # From the metadata:
    (["2050-AG67"], ["2050-AG67"], None),
    # From the XML:
    ([], ["2050-AG68"], ["RIN 2050-AG68"]),
    # From the XML, no prefix:
    ([], ["2050-AG69"], [" 2050-AG69"]),
    # Two numbers:
    (["2050-AG60", "2050-AG61"], ["2050-AG60", "2050-AG61"], None),
    # Two numbers XML:
    ([], ["2050-AG60", "2050-AG61"], ["RIN 2050-AG60", "RIN 2050-AG61"]),
))
def test_rins(rins, expected, xml_rins):
    if not xml_rins:
        xml = _dummy_notice()
    else:
        with XMLBuilder("ROOT") as ctx:
            for xml_rin in xml_rins:
                ctx.RIN(xml_rin)
        xml = notice_xml.NoticeXML(ctx.xml)

    rins = rins or xml.derive_rins()
    xml.rins = rins
    assert xml.rins == expected


@pytest.mark.parametrize('dis,expected,depdoc', (
    # From the metadata:
    (["EPA-HQ-SFUND-2010-1086"], ["EPA-HQ-SFUND-2010-1086"], None),
    # From the XML:
    ([], ["EPA-HQ-SFUND-2010-1086"], "[EPA-HQ-SFUND-2010-1086]"),
    # From the XML, two docket ids:
    ([], ["EPA-HQ-SFUND-2010-1086", "FRL-9925-69-OLEM"],
     "[EPA-HQ-SFUND-2010-1086; FRL-9925-69-OLEM]"),
    # Two docket ids, metadata:
    (["EPA-HQ-SFUND-2010-1086", "FRL-9925-69-OLEM"],
     ["EPA-HQ-SFUND-2010-1086", "FRL-9925-69-OLEM"], None),
))
def test_docket_ids(dis, expected, depdoc):
    if not depdoc:
        xml = _dummy_notice()
    else:
        with XMLBuilder("ROOT") as root:
            root.DEPDOC(depdoc)
        xml = notice_xml.NoticeXML(root.xml)

    dis = dis or xml.derive_docket_ids()
    xml.docket_ids = dis
    assert xml.docket_ids == expected


@pytest.mark.parametrize('refs', (
    [],
    [notice_xml.TitlePartsRef(title=40, parts=[300, 301, 302, 303]),
     notice_xml.TitlePartsRef(title=41, parts=[210]),
     notice_xml.TitlePartsRef(title=42, parts=[302, 303])],
    [notice_xml.TitlePartsRef(title=40, parts=[300, 330]),
     notice_xml.TitlePartsRef(title=41, parts=[210]),
     notice_xml.TitlePartsRef(title=42, parts=[302, 303])],
))
def test_cfr_refs(refs):
    """ Test that we can set and retrieve the same values """
    xml = _dummy_notice()
    xml.cfr_refs = refs
    assert refs == xml.cfr_refs


def test_supporting_documents():
    """Should be able to set and retrieve supporting documents"""
    documents = [RegsGovDoc(str(i), str(i)*3) for i in range(4)]
    notice = _dummy_notice()
    assert notice.supporting_documents == []
    notice.supporting_documents = documents
    assert notice.supporting_documents == documents


def test_derive_where_needed_regs_gov(monkeypatch):
    """Verify that the comment_doc_id, primary_docket and supporting_documents
    get set in the `derive_where_needed` method"""
    monkeypatch.setattr(notice_xml.regs_gov, 'proposal', Mock())
    monkeypatch.setattr(notice_xml.regs_gov, 'supporting_docs', Mock())
    notice = _dummy_notice()
    notice.docket_ids = ['docketdocket']
    notice_xml.regs_gov.proposal.return_value = RegsGovDoc('rrrid', 'A title')
    supporting = [RegsGovDoc('r2', 't2'), RegsGovDoc('r3', 't3')]
    notice_xml.regs_gov.supporting_docs.return_value = supporting

    notice.derive_where_needed()
    assert notice.comment_doc_id == 'rrrid'
    assert notice.primary_docket == 'docketdocket'
    assert notice.supporting_documents == supporting


def test_as_dict():
    with XMLBuilder("ROOT") as ctx:
        ctx.AGENCY('Awesome Admin')
        ctx.SUBJECT('This is the title')

    notice = notice_xml.NoticeXML(ctx.xml)
    notice.cfr_refs = [
        notice_xml.TitlePartsRef(title=11, parts=[234, 456])]
    notice.version_id = 'v1v1v1'
    notice.fr_volume = 33
    notice.start_page = 44
    notice.end_page = 55
    notice.fr_html_url = 'http://example.com'
    notice.published = date(2002, 2, 2)
    notice.comments_close_on = date(2003, 3, 3)
    notice.effective = date(2004, 4, 4)
    notice.rins = ['r1111', 'r2222']
    notice.docket_ids = ['d1111', 'd2222']
    notice.comment_doc_id = 'comment-docket'
    notice.primary_docket = 'd2222'
    notice.supporting_documents = [RegsGovDoc('some-id', 'A support doc')]

    assert notice.as_dict() == {
        'amendments': [],
        'comments_close': '2003-03-03',
        'comment_doc_id': 'comment-docket',
        'cfr_parts': ['234', '456'],
        'cfr_title': 11,
        'dockets': ['d1111', 'd2222'],
        'document_number': 'v1v1v1',
        'effective_on': '2004-04-04',
        'fr_citation': '33 FR 44',
        'fr_url': 'http://example.com',
        'fr_volume': 33,
        'meta': {'start_page': 44},
        'primary_agency': 'Awesome Admin',
        'primary_docket': 'd2222',
        'publication_date': '2002-02-02',
        'regulation_id_numbers': ['r1111', 'r2222'],
        'supporting_documents': [
            {'regs_id': 'some-id', 'title': 'A support doc'}],
        'title': 'This is the title'
    }
