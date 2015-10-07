# vim: set encoding=utf-8
from unittest import TestCase

from regparser.notice import dates
from tests.xml_builder import XMLBuilderMixin


class NoticeDatesTests(XMLBuilderMixin, TestCase):
    def test_parse_date_sentence(self):
        self.assertEqual(('comments', '2009-01-08'),
                         dates.parse_date_sentence(
                             'Comments must be received by January 8, 2009'))
        self.assertEqual(('comments', '2005-02-12'),
                         dates.parse_date_sentence('Comments on the effective '
                                                   'date must be received by '
                                                   'February 12, 2005'))
        self.assertEqual(('effective', '1982-03-01'),
                         dates.parse_date_sentence(
                             'This rule is effective on March 1, 1982'))
        self.assertEqual(('other', '1991-04-30'),
                         dates.parse_date_sentence(
                             "More info will be available on April 30, 1991"))
        self.assertEqual(None,
                         dates.parse_date_sentence('The rule effective on '
                                                   'April 30, 1991 did not '
                                                   'make sense'))

    def test_fetch_dates_no_xml_el(self):
        with self.tree.builder("ROOT") as root:
            root.CHILD()
            root.PREAMB()
        self.assertEqual(None, dates.fetch_dates(self.tree.render_xml()))

    def test_fetch_dates_no_date_text(self):
        with self.tree.builder("ROOT") as root:
            root.CHILD()
            with root.PREAMB() as preamb:
                with preamb.EFFDATE() as effdate:
                    effdate.HD("DATES: ")
                    effdate.P("There are no dates for this.")
        self.assertEqual(None, dates.fetch_dates(self.tree.render_xml()))

    def test_fetch_dates_emphasis(self):
        with self.tree.builder("ROOT") as root:
            with root.DATES() as dates_xml:
                dates_xml.HD("DATES:", SOURCE="HED")
                dates_xml.P(_xml=("<E T='03'>Effective date:</E>"
                                  "The rule is effective June 1, 2077"))
                dates_xml.P(_xml=(
                    "<E T='03'>Applicability date:</E>"
                    "Its requirements apply to things after that date."))
        self.assertEqual(dates.fetch_dates(self.tree.render_xml()),
                         {'effective': ['2077-06-01']})

    def test_fetch_dates(self):
        with self.tree.builder("ROOT") as root:
            root.CHILD()
            with root.PREAMB() as preamb:
                with preamb.EFFDATE() as effdate:
                    effdate.HD("DATES: ")
                    effdate.P("We said stuff that's effective on May 9, "
                              "2005. If you'd like to add comments, please "
                              "do so by June 3, 1987.  Wait, that doesn't "
                              "make sense. I mean, the comment period ends "
                              "on July 9, 2004. Whew. It would have been "
                              "more confusing if I said August 15, 2005. "
                              "Right?")
        self.assertEqual(dates.fetch_dates(self.tree.render_xml()), {
            'effective': ['2005-05-09'],
            'comments': ['1987-06-03', '2004-07-09'],
            'other': ['2005-08-15']
        })

    def test_set_effective_date(self):
        """Effective date attribute should be set within the XML. If one isn't
        provided, we should attempt to derive it"""
        with self.tree.builder("ROOT") as root:
            with root.EFFDATE() as effdate:
                effdate.P("Effective on May 4, 2004")
        xml = self.tree.render_xml()

        self.assertEqual("2005-05-05",
                         dates.set_effective_date(xml, "2005-05-05"))
        self.assertEqual(xml.xpath("//EFFDATE")[0].get("eregs-effective-date"),
                         "2005-05-05")

        self.assertEqual("2004-05-04", dates.set_effective_date(xml))
        self.assertEqual(xml.xpath("//EFFDATE")[0].get("eregs-effective-date"),
                         "2004-05-04")

    def test_set_effective_date_create(self):
        """The EFFDATE tag should get created if not present in the XML"""
        with self.tree.builder("ROOT") as root:
            with root.DATES() as effdate:
                effdate.P("Effective on May 4, 2004")
        xml = self.tree.render_xml()

        self.assertEqual("2004-05-04", dates.set_effective_date(xml))
        self.assertEqual(xml.xpath("//EFFDATE")[0].get("eregs-effective-date"),
                         "2004-05-04")
