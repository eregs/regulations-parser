from datetime import date
import os
import shutil
import tempfile
from unittest import TestCase

from mock import patch

from regparser.history.delays import FRDelay
from regparser.notice import xml as notice_xml
from regparser.regs_gov import RegsGovDoc
from regparser.test_utils.xml_builder import XMLBuilder
import settings


class NoticeXMLLocalCopiesTests(TestCase):
    """Tests specifically related to xml.local_copies, which has significant
    setup/teardown"""
    def setUp(self):
        self.dir1 = tempfile.mkdtemp()
        self.dir2 = tempfile.mkdtemp()
        self._original_local_xml_paths = settings.LOCAL_XML_PATHS
        settings.LOCAL_XML_PATHS = [self.dir1, self.dir2]
        self.url = 'http://example.com/some/url'

    def tearDown(self):
        settings.LOCAL_XML_PATHS = self._original_local_xml_paths
        shutil.rmtree(self.dir1)
        shutil.rmtree(self.dir2)

    def test_empty(self):
        """If no copy is present, we get an empty list"""
        self.assertEqual([], notice_xml.local_copies(self.url))

        os.mkdir(os.path.join(self.dir1, "some"))
        self.assertEqual([], notice_xml.local_copies(self.url))

    def test_order(self):
        """The first source will override the second"""
        url = 'http://example.com/some/url'
        paths = []
        for d in (self.dir1, self.dir2):
            os.mkdir(os.path.join(d, "some"))
            paths.append(os.path.join(d, "some", "url"))

        with open(paths[1], "w") as f:
            f.write('aaaaa')
        self.assertEqual([paths[1]], notice_xml.local_copies(url))

        with open(paths[0], "w") as f:
            f.write('bbbbb')
        self.assertEqual([paths[0]], notice_xml.local_copies(url))

    def test_splits(self):
        """If multiple files are present from a single source, return all"""
        url = 'http://example.com/xml/503.xml'
        os.mkdir(os.path.join(self.dir1, 'xml'))
        paths = []
        for i in range(3):
            path = os.path.join(self.dir1, 'xml', '503-{}.xml'.format(i + 1))
            paths.append(path)
            with open(path, 'w') as f:
                f.write(str(i)*10)

        self.assertEqual(set(paths), set(notice_xml.local_copies(url)))


class NoticeXMLTests(TestCase):
    """Tests for the NoticeXML class"""
    def _dummy_notice(self):
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Some content")
            ctx.PRTPAGE(P="455")
        return notice_xml.NoticeXML(ctx.xml)

    def test_set_meta_data(self):
        """Several pieces of meta data should be set within the XML. We test
        that the NoticeXML wrapper can retrieve them and that, if we re-read
        the XML, they can still be pulled out"""
        xml = self._dummy_notice()

        xml.effective = '2005-05-05'
        xml.published = '2004-04-04'
        xml.fr_volume = 22

        self.assertEqual(xml.effective, date(2005, 5, 5))
        self.assertEqual(xml.published, date(2004, 4, 4))
        self.assertEqual(xml.fr_volume, 22)

        xml = notice_xml.NoticeXML(xml.xml)
        self.assertEqual(xml.effective, date(2005, 5, 5))
        self.assertEqual(xml.published, date(2004, 4, 4))
        self.assertEqual(xml.fr_volume, 22)

    def test_set_effective_date_create(self):
        """The DATES tag should get created if not present in the XML"""
        xml = self._dummy_notice()

        xml.effective = '2005-05-05'
        self.assertEqual(xml.effective, date(2005, 5, 5))
        xml = notice_xml.NoticeXML(xml.xml)
        self.assertEqual(xml.effective, date(2005, 5, 5))

    def test_derive_effective_date(self):
        """Effective date can be derived from the dates strings. When it is
        derived, it should also be set on the notice xml"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective on May 4, 2004")
        xml = notice_xml.NoticeXML(ctx.xml)

        xml.effective = '2002-02-02'
        self.assertEqual(xml.derive_effective_date(), date(2004, 5, 4))
        # does _not_ set that date
        self.assertEqual(xml.effective, date(2002, 2, 2))
        xml.effective = xml.derive_effective_date()
        self.assertEqual(xml.effective, date(2004, 5, 4))

    def test_delays(self):
        """The XML should be search for any delaying text"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.EFFDATE():
                ctx.P("The effective date of 11 FR 100 has been delayed "
                      "until April 1, 2010. The effective date of 11 FR 200 "
                      "has also been delayed until October 10, 2010")
        xml = notice_xml.NoticeXML(ctx.xml)

        self.assertEqual(
            xml.delays(),
            [FRDelay(11, 100, date(2010, 4, 1)),
             FRDelay(11, 200, date(2010, 10, 10))])

    def test_set_agencies_simple(self):
        """
        Test that we can properly derive agency info from the metadata or the
        XML itself, and that it's added to the XML.
        """
        agencies_info = [{
            u'name': u'Environmental Protection Agency',
            u'parent_id': None,
            u'raw_name': u'ENVIRONMENTAL PROTECTION AGENCY',
            u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                               u'agencies/environmental-protection-agency'),
            u'json_url': u'%s%s' % ('https://www.federalregister.gov/',
                                    'api/v1/agencies/145.json'),
            u'id': 145
        }]
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective on May 4, 2004")
        xml = notice_xml.NoticeXML(ctx.xml)
        xml.set_agencies(agencies=agencies_info)
        self.assertEquals(len(xml.xpath("//EREGS_AGENCIES")), 1)
        eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
        self.assertEquals(len(eregs_agencies.xpath("//EREGS_AGENCY")), 1)
        epa = eregs_agencies.xpath("//EREGS_AGENCY")[0]
        self.assertEquals(epa.attrib["name"],
                          "Environmental Protection Agency")
        self.assertEquals(epa.attrib["raw-name"],
                          "ENVIRONMENTAL PROTECTION AGENCY")
        self.assertEquals(epa.attrib["agency-id"], "145")

    def test_set_agencies_singlesub(self):
        """
        Test that we can properly derive agency info from the metadata and add
        it to the XML if there is a subagency.
        """
        agencies_info = [
            {
                u'name': u'Justice Department',
                u'parent_id': None,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/justice-department'),
                u'raw_name': u'DEPARTMENT OF JUSTICE',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/268.json'),
                u'id': 268
            },
            {
                u'name': u'Alcohol, Tobacco, Firearms, and Explosives Bureau',
                u'parent_id': 268,
                u'url': '%s%s%s' % (u'https://www.federalregister.gov/',
                                    u'agencies/alcohol-tobacco-firearms',
                                    u'-and-explosives-bureau'),
                u'raw_name': '%s%s' % (u'Bureau of Alcohol, Tobacco, Firearms',
                                       u' and Explosives'),
                u'json_url': '%s%s' % (u'https://www.federalregister.gov/',
                                       u'api/v1/agencies/19.json'),
                u'id': 19
            }
        ]
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective on May 4, 2004")
        xml = notice_xml.NoticeXML(ctx.xml)
        xml.set_agencies(agencies=agencies_info)
        self.assertEquals(len(xml.xpath("//EREGS_AGENCIES")), 1)
        eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
        self.assertEquals(len(eregs_agencies.xpath("//EREGS_AGENCY")), 1)
        doj = eregs_agencies.xpath("//EREGS_AGENCY")[0]
        self.assertEquals(doj.attrib["name"], "Justice Department")
        self.assertEquals(doj.attrib["raw-name"], "DEPARTMENT OF JUSTICE")
        self.assertEquals(doj.attrib["agency-id"], "268")
        self.assertEquals(len(doj.xpath("//EREGS_SUBAGENCY")), 1)
        atf = doj.xpath("//EREGS_SUBAGENCY")[0]
        self.assertEquals(atf.attrib["name"],
                          "Alcohol, Tobacco, Firearms, and Explosives Bureau")
        self.assertEquals(
            atf.attrib["raw-name"],
            "Bureau of Alcohol, Tobacco, Firearms and Explosives")
        self.assertEquals(atf.attrib["agency-id"], "19")

    def test_set_agencies_unrelated(self):
        """
        Test that we can properly derive agency info from the metadata and add
        it to the XML if there is an agency and a non-child subagency.
        """
        agencies_info = [
            {
                u'name': u'Treasury Department',
                u'parent_id': None,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/treasury-department'),
                u'raw_name': u'DEPARTMENT OF THE TREASURY',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/497.json'),
                u'id': 497
            },
            {
                u'name': u'Alcohol, Tobacco, Firearms, and Explosives Bureau',
                u'parent_id': 268,
                u'url': '%s%s%s' % (u'https://www.federalregister.gov/',
                                    u'agencies/alcohol-tobacco-firearms',
                                    u'-and-explosives-bureau'),
                u'raw_name': '%s%s' % (u'Bureau of Alcohol, Tobacco, Firearms',
                                       u' and Explosives'),
                u'json_url': '%s%s' % (u'https://www.federalregister.gov/',
                                       u'api/v1/agencies/19.json'),
                u'id': 19
            }
        ]
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective on May 4, 2004")
        xml = notice_xml.NoticeXML(ctx.xml)
        xml.set_agencies(agencies=agencies_info)
        self.assertEquals(len(xml.xpath("//EREGS_AGENCIES")), 1)
        eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
        self.assertEquals(len(eregs_agencies.xpath("//EREGS_AGENCY")), 1)
        treas = eregs_agencies.xpath("//EREGS_AGENCY")[0]
        self.assertEquals(treas.attrib["name"], "Treasury Department")
        self.assertEquals(treas.attrib["raw-name"],
                          "DEPARTMENT OF THE TREASURY")
        self.assertEquals(treas.attrib["agency-id"], "497")
        self.assertEquals(len(eregs_agencies.xpath("//EREGS_SUBAGENCY")), 1)
        atf = eregs_agencies.xpath("//EREGS_SUBAGENCY")[0]
        self.assertEquals(atf.attrib["name"],
                          u'Alcohol, Tobacco, Firearms, and Explosives Bureau')
        self.assertEquals(
            atf.attrib["raw-name"],
            u"Bureau of Alcohol, Tobacco, Firearms and Explosives")
        self.assertEquals(atf.attrib["agency-id"], "19")

    def test_set_agencies_mixed(self):
        """
        Test that we can properly derive agency info from the metadata and add
        it to the XML if we have a parent-child relationship and an unrelated
        agency.
        """
        agencies_info = [
            {
                u'name': u'Treasury Department',
                u'parent_id': None,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/treasury-department'),
                u'raw_name': u'DEPARTMENT OF THE TREASURY',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/497.json'),
                u'id': 497
            },
            {
                u'name': u'Alcohol, Tobacco, Firearms, and Explosives Bureau',
                u'parent_id': 268,
                u'url': '%s%s%s' % (u'https://www.federalregister.gov/',
                                    u'agencies/alcohol-tobacco-firearms',
                                    u'-and-explosives-bureau'),
                u'raw_name': '%s%s' % (u'Bureau of Alcohol, Tobacco, Firearms',
                                       u' and Explosives'),
                u'json_url': '%s%s' % (u'https://www.federalregister.gov/',
                                       u'api/v1/agencies/19.json'),
                u'id': 19
            },
            {
                u'name': u'Justice Department',
                u'parent_id': None,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/justice-department'),
                u'raw_name': u'DEPARTMENT OF JUSTICE',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/268.json'),
                u'id': 268
            }
        ]
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective on May 4, 2004")
        xml = notice_xml.NoticeXML(ctx.xml)
        xml.set_agencies(agencies=agencies_info)
        self.assertEquals(len(xml.xpath("//EREGS_AGENCIES")), 1)
        eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
        self.assertEquals(len(eregs_agencies.xpath("//EREGS_AGENCY")), 2)
        treas = eregs_agencies.xpath("//EREGS_AGENCY")[0]
        self.assertEquals(treas.attrib["name"], "Treasury Department")
        self.assertEquals(treas.attrib["raw-name"],
                          "DEPARTMENT OF THE TREASURY")
        self.assertEquals(treas.attrib["agency-id"], "497")
        doj = eregs_agencies.xpath("//EREGS_AGENCY")[1]
        self.assertEquals(doj.attrib["name"], "Justice Department")
        self.assertEquals(doj.attrib["raw-name"], "DEPARTMENT OF JUSTICE")
        self.assertEquals(doj.attrib["agency-id"], "268")
        self.assertEquals(len(doj.xpath("//EREGS_SUBAGENCY")), 1)
        atf = doj.xpath("//EREGS_SUBAGENCY")[0]
        self.assertEquals(atf.attrib["name"],
                          u'Alcohol, Tobacco, Firearms, and Explosives Bureau')
        self.assertEquals(
            atf.attrib["raw-name"],
            u"Bureau of Alcohol, Tobacco, Firearms and Explosives")
        self.assertEquals(atf.attrib["agency-id"], "19")

    def test_set_agencies_generations(self):
        """
        Test that we can properly derive agency info from the metadata and add
        it to the XML if we have nested parent-child relationships.
        """
        agencies_info = [
            {
                u'name': u'ATF subagency',
                u'parent_id': 19,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/atf-subagency'),
                u'raw_name': u'SUBAGENCY OF ATF',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/100023.json'),
                u'id': 100023
            },
            {
                u'name': u'Alcohol, Tobacco, Firearms, and Explosives Bureau',
                u'parent_id': 268,
                u'url': '%s%s%s' % (u'https://www.federalregister.gov/',
                                    u'agencies/alcohol-tobacco-firearms',
                                    u'-and-explosives-bureau'),
                u'raw_name': '%s%s' % (u'Bureau of Alcohol, Tobacco, Firearms',
                                       u' and Explosives'),
                u'json_url': '%s%s' % (u'https://www.federalregister.gov/',
                                       u'api/v1/agencies/19.json'),
                u'id': 19
            },
            {
                u'name': u'Justice Department',
                u'parent_id': None,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/justice-department'),
                u'raw_name': u'DEPARTMENT OF JUSTICE',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/268.json'),
                u'id': 268
            },
            {
                u'name': u'ATF subsubagency',
                u'parent_id': 100023,
                u'url': u'%s%s' % (u'https://www.federalregister.gov/',
                                   u'agencies/atf-subsubagency'),
                u'raw_name': u'SUBSUBAGENCY OF ATF',
                u'json_url': u'%s%s' % (u'https://www.federalregister.gov/',
                                        u'api/v1/agencies/100072.json'),
                u'id': 100072
            },
        ]
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective on May 4, 2004")
        xml = notice_xml.NoticeXML(ctx.xml)
        xml.set_agencies(agencies=agencies_info)
        self.assertEquals(len(xml.xpath("//EREGS_AGENCIES")), 1)
        eregs_agencies = xml.xpath("//EREGS_AGENCIES")[0]
        self.assertEquals(len(eregs_agencies.xpath("//EREGS_AGENCY")), 1)
        doj = eregs_agencies.xpath("//EREGS_AGENCY")[0]
        self.assertEquals(doj.attrib["name"], "Justice Department")
        self.assertEquals(doj.attrib["raw-name"], "DEPARTMENT OF JUSTICE")
        self.assertEquals(doj.attrib["agency-id"], "268")
        self.assertEquals(len(doj.xpath("//EREGS_SUBAGENCY")), 3)
        self.assertEquals(len(doj.xpath("EREGS_SUBAGENCY")), 1)
        atf = doj.xpath("//EREGS_SUBAGENCY")[0]
        self.assertEquals(atf.attrib["name"],
                          u'Alcohol, Tobacco, Firearms, and Explosives Bureau')
        self.assertEquals(
            atf.attrib["raw-name"],
            "Bureau of Alcohol, Tobacco, Firearms and Explosives")
        self.assertEquals(atf.attrib["agency-id"], "19")
        self.assertEquals(len(atf.xpath("EREGS_SUBAGENCY")), 1)
        subatf = atf.xpath("EREGS_SUBAGENCY")[0]
        self.assertEquals(subatf.attrib["name"], u'ATF subagency')
        self.assertEquals(subatf.attrib["raw-name"], u"SUBAGENCY OF ATF")
        self.assertEquals(subatf.attrib["agency-id"], u"100023")
        subsubatf = subatf.xpath("EREGS_SUBAGENCY")[0]
        self.assertEquals(subsubatf.attrib["name"], u'ATF subsubagency')
        self.assertEquals(subsubatf.attrib["raw-name"], u"SUBSUBAGENCY OF ATF")
        self.assertEquals(subsubatf.attrib["agency-id"], u"100072")

    def test_rins(self):
        def rinstest(rins, expected, xml=None):
            if not xml:
                xml = self._dummy_notice()
            rins = rins or xml.derive_rins()
            xml.rins = rins
            self.assertEquals(expected, xml.rins)

        # From the metadata:
        rinstest(["2050-AG67"], ["2050-AG67"])

        # From the XML:
        with XMLBuilder("ROOT") as root:
            root.RIN("RIN 2050-AG68")
        xml = notice_xml.NoticeXML(root.xml)
        rinstest([], ["2050-AG68"], xml=xml)

        # From the XML, no prefix:
        with XMLBuilder("ROOT") as root:
            root.RIN(" 2050-AG69")
        xml = notice_xml.NoticeXML(root.xml)
        rinstest([], ["2050-AG69"], xml=xml)

        # Two numbers:
        rinstest(["2050-AG60", "2050-AG61"], ["2050-AG60", "2050-AG61"])

        # Two numbers XML:
        with XMLBuilder("ROOT") as root:
            root.RIN("RIN 2050-AG60")
            root.RIN("RIN 2050-AG61")
        xml = notice_xml.NoticeXML(root.xml)
        rinstest([], ["2050-AG60", "2050-AG61"],
                 xml=xml)

    def test_docket_ids(self):
        def ditest(dis, expected, xml=None):
            if not xml:
                xml = self._dummy_notice()
            dis = dis or xml.derive_docket_ids()
            xml.docket_ids = dis
            self.assertEquals(expected, xml.docket_ids)

        # From the metadata:
        ditest(["EPA-HQ-SFUND-2010-1086"], ["EPA-HQ-SFUND-2010-1086"])

        # From the XML:
        with XMLBuilder("ROOT") as root:
            root.DEPDOC("[EPA-HQ-SFUND-2010-1086]")
        xml = notice_xml.NoticeXML(root.xml)
        ditest([], ["EPA-HQ-SFUND-2010-1086"], xml=xml)

        # From the XML, two docket ids:
        with XMLBuilder("ROOT") as root:
            root.DEPDOC("[EPA-HQ-SFUND-2010-1086; FRL-9925-69-OLEM]")
        xml = notice_xml.NoticeXML(root.xml)
        ditest([], ["EPA-HQ-SFUND-2010-1086", "FRL-9925-69-OLEM"], xml=xml)

        # Two docket ids, metadata:
        ditest(["EPA-HQ-SFUND-2010-1086", "FRL-9925-69-OLEM"],
               ["EPA-HQ-SFUND-2010-1086", "FRL-9925-69-OLEM"])

    def test_cfr_refs(self):
        """
        Test that we can set and retrieve the same values
        """
        def _reftest(refs):
            xml = self._dummy_notice()
            xml.cfr_refs = refs
            self.assertEqual(refs, xml.cfr_refs)

        _reftest([])
        _reftest([
            notice_xml.TitlePartsRef(title=40, parts=[300, 301, 302, 303]),
            notice_xml.TitlePartsRef(title=41, parts=[210]),
            notice_xml.TitlePartsRef(title=42, parts=[302, 303])
        ])
        _reftest([
            notice_xml.TitlePartsRef(title=40, parts=[300, 330]),
            notice_xml.TitlePartsRef(title=41, parts=[210]),
            notice_xml.TitlePartsRef(title=42, parts=[302, 303])
        ])

    def test_supporting_documents(self):
        """Should be able to set and retrieve supporting documents"""
        documents = [RegsGovDoc(str(i), str(i)*3) for i in range(4)]
        notice = self._dummy_notice()
        self.assertEqual([], notice.supporting_documents)
        notice.supporting_documents = documents
        self.assertEqual(documents, notice.supporting_documents)

    @patch('regparser.notice.xml.regs_gov.supporting_docs')
    @patch('regparser.notice.xml.regs_gov.proposal')
    def test_derive_where_needed_regs_gov(self, mock_proposal,
                                          mock_supporting_docs):
        """Verify that the comment_doc_id, primary_docket and
        supporting_documents get set in the `derive_where_needed` method"""
        notice = self._dummy_notice()
        notice.docket_ids = ['docketdocket']
        mock_proposal.return_value = RegsGovDoc('rrrid', 'A title')
        supporting = [RegsGovDoc('r2', 't2'), RegsGovDoc('r3', 't3')]
        mock_supporting_docs.return_value = supporting

        notice.derive_where_needed()
        self.assertEqual(notice.comment_doc_id, 'rrrid')
        self.assertEqual(notice.primary_docket, 'docketdocket')
        self.assertEqual(notice.supporting_documents, supporting)

    def test_as_dict(self):
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

        self.assertEqual(notice.as_dict(), {
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
        })
