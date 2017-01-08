# vim: set encoding=utf-8
import re
from unittest import TestCase

from mock import Mock, patch

from regparser.history import annual
from regparser.test_utils.http_mixin import HttpMixin


class HistoryAnnualVolumeTests(HttpMixin, TestCase):
    def test_init(self):
        uri = re.compile(r'.*gpo.gov.*1010.*12.*4.*xml')
        self.expect_xml_http(uri=uri)
        volume = annual.Volume(1010, 12, 4)
        self.assertEqual(True, volume.exists)

        self.expect_xml_http(status=404, uri=uri)
        volume = annual.Volume(1010, 12, 4)
        self.assertEqual(False, volume.exists)

    def test_should_contain1(self):
        self.expect_xml_http("""
        <CFRDOC>
            <AMDDATE>Jan 1, 2001</AMDDATE>
            <PARTS>Part 111 to 222</PARTS>
        </CFRDOC>""")

        volume = annual.Volume(2001, 12, 2)
        self.assertFalse(volume.should_contain(1))
        self.assertFalse(volume.should_contain(100))
        self.assertFalse(volume.should_contain(300))
        self.assertFalse(volume.should_contain(250))
        self.assertTrue(volume.should_contain(111))
        self.assertTrue(volume.should_contain(211))
        self.assertTrue(volume.should_contain(222))

        self.expect_xml_http("""
        <CFRDOC>
            <AMDDATE>Jan 1, 2001</AMDDATE>
            <PARTS>Parts 587 to End</PARTS>
        </CFRDOC>""")

        volume = annual.Volume(2001, 12, 2)
        self.assertFalse(volume.should_contain(111))
        self.assertFalse(volume.should_contain(586))
        self.assertTrue(volume.should_contain(587))
        self.assertTrue(volume.should_contain(600))
        self.assertTrue(volume.should_contain(999999))

    def test_should_contain2(self):
        pt111 = """
        <PART>
            <EAR>Pt. 111</EAR>
            <HD SOURCE="HED">PART 111-Something</HD>
            <FIELD>111 Content</FIELD>
        </PART>"""
        pt112 = """
        <PART>
            <EAR>Pt. 112</EAR>
            <HD SOURCE="HED">PART 112-Something</HD>
            <FIELD>112 Content</FIELD>
        </PART>"""

        self.expect_xml_http(pt111, uri=re.compile(r".*part111\.xml"))
        self.expect_xml_http(pt112, uri=re.compile(r".*part112\.xml"))
        self.expect_xml_http(status=404, uri=re.compile(r".*part113\.xml"))
        self.expect_xml_http("""
        <CFRDOC>
            <AMDDATE>Jan 1, 2001</AMDDATE>
            <PARTS>Part 111 to 222</PARTS>
            {0}
            {1}
        </CFRDOC>""".format(pt111, pt112), uri=re.compile(r".*bulkdata.*"))

        volume = annual.Volume(2001, 12, 2)

        xml = volume.find_part_xml(111)
        self.assertEqual(len(xml.xpath('./EAR')), 1)
        self.assertEqual(xml.xpath('./EAR')[0].text, 'Pt. 111')
        self.assertEqual(len(xml.xpath('./FIELD')), 1)
        self.assertEqual(xml.xpath('./FIELD')[0].text, '111 Content')

        xml = volume.find_part_xml(112)
        self.assertEqual(len(xml.xpath('./EAR')), 1)
        self.assertEqual(xml.xpath('./EAR')[0].text, 'Pt. 112')
        self.assertEqual(len(xml.xpath('./FIELD')), 1)
        self.assertEqual(xml.xpath('./FIELD')[0].text, '112 Content')

        self.assertEqual(volume.find_part_xml(113), None)

    def test_should_contain_with_single_part(self):
        self.expect_xml_http("""
                <CFRDOC>
                    <AMDDATE>Jan 1, 2001</AMDDATE>
                    <PARTS>Part 641 (§§ 641.1 to 641.599)</PARTS>
                </CFRDOC>""")

        volume = annual.Volume(2001, 12, 2)
        self.assertFalse(volume.should_contain(640))
        self.assertTrue(volume.should_contain(641))
        self.assertFalse(volume.should_contain(642))

    def test_should_contain__empty_volume(self):
        """If the first volume does not contain a PARTS tag, we should assume
        that it covers all of the regs in this title"""
        self.expect_xml_http("""
        <CFRDOC>
            <SOMETHINGELSE>Here</SOMETHINGELSE>
        </CFRDOC>
        """, uri=re.compile(r".*bulkdata.*"))

        volume = annual.Volume(2001, 12, 1)
        self.assertTrue(volume.should_contain(1))
        self.assertTrue(volume.should_contain(10))
        self.assertTrue(volume.should_contain(100))
        self.assertTrue(volume.should_contain(1000))

    @patch('regparser.history.annual.http_client')
    def test_find_part_local(self, http_client):
        """Verify that a local copy of the annual edition content is
        checked"""
        http_client.return_value.get.return_value.status_code = 200
        http_client.return_value.get.return_value.content = b"""
        <PART>
            <EAR>Pt. 111</EAR>
            <HD SOURCE="HED">PART 111-Something</HD>
            <FIELD>111 Content</FIELD>
        </PART>"""
        volume = annual.Volume(2001, 12, 1)

        volume.find_part_xml(111)
        assert http_client.return_value.get.call_count == 1

        http_client.return_value.get.return_value.status_code = 404
        volume.find_part_xml(111)
        assert http_client.return_value.get.call_count == 3


class HistoryAnnualTests(TestCase):
    @patch('regparser.history.annual.Volume')
    def test_find_volume(self, mock_volume):
        v1 = Mock()
        v1.exists = True
        v1.should_contain.return_value = False

        v2 = Mock()
        v2.exists = True
        v2.should_contain.return_value = True

        v3 = Mock()
        v3.exists = False

        def side_effect(year, title, vol_num):
            if vol_num > 3:
                return v2
            return v1
        mock_volume.side_effect = side_effect

        self.assertEqual(annual.find_volume(2000, 11, 3), v2)

        def side_effect(year, title, vol_num):
            if vol_num > 3:
                return v3
            return v1
        mock_volume.side_effect = side_effect
        self.assertEqual(annual.find_volume(2000, 11, 3), None)
