from datetime import date
import os
import shutil
import tempfile
from unittest import TestCase

from regparser.history.delays import FRDelay
from regparser.notice import xml as notice_xml
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
    def test_set_meta_data(self):
        """Several pieces of meta data should be set within the XML. We test
        that the NoticeXML wrapper can retrieve them and that, if we re-read
        the XML, they can still be pulled out"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Some content")
            ctx.PRTPAGE(P="455")
        xml = notice_xml.NoticeXML(ctx.xml)

        xml.effective = '2005-05-05'
        xml.published = '2004-04-04'
        xml.fr_volume = 22

        self.assertEqual(xml.effective, date(2005, 5, 5))
        self.assertEqual(xml.published, date(2004, 4, 4))
        self.assertEqual(xml.fr_volume, 22)

        xml = notice_xml.NoticeXML(xml.xml_str())
        self.assertEqual(xml.effective, date(2005, 5, 5))
        self.assertEqual(xml.published, date(2004, 4, 4))
        self.assertEqual(xml.fr_volume, 22)

    def test_set_effective_date_create(self):
        """The DATES tag should get created if not present in the XML"""
        xml = notice_xml.NoticeXML(XMLBuilder('ROOT').xml)

        xml.effective = '2005-05-05'
        self.assertEqual(xml.effective, date(2005, 5, 5))
        xml = notice_xml.NoticeXML(xml.xml_str())
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

    def test_source_is_local(self):
        for url in ('https://example.com', 'http://example.com'):
            self.assertFalse(
                notice_xml.NoticeXML('<ROOT/>', source=url).source_is_local)
        for path in ('./dot/relative', 'normal/relative', '/absolute/ref'):
            self.assertTrue(
                notice_xml.NoticeXML('<ROOT/>', source=path).source_is_local)
