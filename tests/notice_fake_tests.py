from unittest import TestCase

from lxml import etree

from regparser.notice import fake


class NoticeFakeTests(TestCase):
    def test_effective_date_for(self):
        """This function should be able to pull the effective date out of a
        few places"""
        xml = etree.fromstring("""
            <ROOT>
                <P>CONTENT</P>
                <DATE>1999-02-03</DATE>
                <ORIGINALDATE>1988-06-07</ORIGINALDATE>
            </ROOT>""")
        self.assertEqual(fake.effective_date_for(xml), '1999-02-03')

        xml = etree.fromstring("""
            <ROOT>
                <P>CONTENT</P>
                <ORIGINALDATE>1988-06-07</ORIGINALDATE>
            </ROOT>""")
        self.assertEqual(fake.effective_date_for(xml), '1988-06-07')
