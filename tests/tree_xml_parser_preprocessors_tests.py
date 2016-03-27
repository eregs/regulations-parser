# vim: set encoding=utf-8
from unittest import TestCase

from lxml import etree

from regparser.tree.xml_parser import preprocessors
from tests.xml_builder import XMLBuilderMixin


class MoveLastAMDParTests(XMLBuilderMixin, TestCase):
    def test_improper_amdpar_location(self):
        """The second AMDPAR is in the wrong parent; it should be moved"""
        with self.tree.builder("PART") as part:
            with part.REGTEXT(ID="RT1") as regtext:
                regtext.AMDPAR(u"1. In § 105.1, revise paragraph (b):")
                with regtext.SECTION() as section:
                    section.P("Some Content")
                # Note this has the wrong parent
                regtext.AMDPAR(u"3. In § 105.2, revise paragraph (a) to read:")
            with part.REGTEXT(ID="RT2") as regtext:
                with regtext.SECTION() as section:
                    section.P("Other Content")
        xml = self.tree.render_xml()

        preprocessors.MoveLastAMDPar().transform(xml)

        amd1, amd2 = xml.xpath("//AMDPAR")
        self.assertEqual(amd1.getparent().get("ID"), "RT1")
        self.assertEqual(amd2.getparent().get("ID"), "RT2")

    def test_trick_amdpar_location_diff_parts(self):
        """Similar situation to the above, except the regulations describe
        different parts and hence the AMDPAR should not move"""
        with self.tree.builder("PART") as part:
            with part.REGTEXT(ID="RT1", PART="105") as regtext:
                regtext.AMDPAR(u"1. In § 105.1, revise paragraph (b):")
                with regtext.SECTION() as section:
                    section.P("Some Content")
                regtext.AMDPAR(u"3. In § 105.2, revise paragraph (a) to read:")
            with part.REGTEXT(ID="RT2", PART="107") as regtext:
                with regtext.SECTION() as section:
                    section.P("Other Content")
        xml = self.tree.render_xml()

        preprocessors.MoveLastAMDPar().transform(xml)

        amd1, amd2 = xml.xpath("//AMDPAR")
        self.assertEqual(amd1.getparent().get("ID"), "RT1")
        self.assertEqual(amd2.getparent().get("ID"), "RT1")


class SupplementAMDParTests(XMLBuilderMixin, TestCase):
    def test_incorrect_ps(self):
        """Supplement I AMDPARs are not always labeled as should be"""
        with self.tree.builder("PART") as part:
            with part.REGTEXT() as regtext:
                regtext.AMDPAR(u"1. In § 105.1, revise paragraph (b):")
                with regtext.SECTION() as section:
                    section.STARS()
                    section.P("(b) Content")
                regtext.P("2. In Supplement I to Part 105,")
                regtext.P("A. Under Section 105.1, 1(b), paragraph 2 is "
                          "revised")
                regtext.P("The revisions are as follows")
                regtext.HD("Supplement I to Part 105", SOURCE="HD1")
                regtext.STARS()
                with regtext.P() as p:
                    p.E("1(b) Heading", T="03")
                regtext.STARS()
                regtext.P("2. New Context")
        xml = self.tree.render_xml()

        preprocessors.SupplementAMDPar().transform(xml)

        # Note that the SECTION paragraphs were not converted
        self.assertEqual(
            [amd.text for amd in xml.xpath("//AMDPAR")],
            [u"1. In § 105.1, revise paragraph (b):",
             "2. In Supplement I to Part 105,",
             "A. Under Section 105.1, 1(b), paragraph 2 is revised",
             "The revisions are as follows"])


class ParenthesesCleanupTests(XMLBuilderMixin, TestCase):
    def assert_transformed(self, original, new_text):
        """Helper function to verify that the XML is transformed as
        expected"""
        self.setUp()
        with self.tree.builder("PART") as part:
            part.P(_xml=original)
        xml = self.tree.render_xml()
        preprocessors.ParenthesesCleanup().transform(xml)
        self.assertEqual("<P>{}</P>".format(new_text),
                         etree.tostring(xml[0]))

    def test_transform(self):
        """The parens should always move out"""
        expected = '(<E T="03">a</E>) Content'
        self.assert_transformed('(<E T="03">a</E>) Content', expected)
        self.assert_transformed('(<E T="03">a)</E> Content', expected)
        self.assert_transformed('<E T="03">(a</E>) Content', expected)
        self.assert_transformed('<E T="03">(a)</E> Content', expected)
        self.assert_transformed('<E T="03">Paragraph 22(a)(5)</E> Content',
                                '<E T="03">Paragraph 22(a)(5)</E> Content')


class MoveAdjoiningCharsTests(XMLBuilderMixin, TestCase):
    def assert_transformed(self, input_xml, expected_xml):
        self.setUp()
        input_xml = input_xml.decode('utf-8')
        with self.tree.builder("SECTION") as section:
            section.P(_xml=input_xml)
        xml = self.tree.render_xml()
        preprocessors.MoveAdjoiningChars().transform(xml)
        self.assertEqual(etree.tostring(
                         xml.xpath('./P/E')[0], encoding='UTF-8'),
                         expected_xml)

    def test_transform(self):
        self.assert_transformed('<E T="03">Things</E>— more things',
                                '<E T="03">Things—</E> more things')
        self.assert_transformed('<E T="03">Things</E>.',
                                '<E T="03">Things.</E>')
        self.assert_transformed('<E T="03">Things</E>. more things',
                                '<E T="03">Things.</E> more things')
        self.assert_transformed('<E T="03">Things</E>. more things.',
                                '<E T="03">Things.</E> more things.')
        self.assert_transformed('<E T="03">Things</E>',
                                '<E T="03">Things</E>')


class ApprovalsFPTests(XMLBuilderMixin, TestCase):
    def control_number(self, number, prefix="Approved"):
        return ("({} by the Office of Management and Budget under "
                "control number {})".format(prefix, number))

    def test_transform(self):
        """Verify that FP tags get transformed, but only if they match a
        certain string"""
        with self.tree.builder("PART") as part:
            part.APPRO(self.control_number('1111-2222'))
            part.FP("Something else")
            part.FP(self.control_number('2222-4444'))
            part.P(self.control_number('3333-6666'))
            with part.EXTRACT() as extract:
                extract.FP(self.control_number(
                    "4444-8888", "Paragraph (b)(2) approved"))
            part.P(self.control_number('4444-8888'))
        xml = self.tree.render_xml()
        preprocessors.ApprovalsFP().transform(xml)
        appros = [appro.text for appro in xml.xpath("./APPRO")]
        self.assertEqual(appros, [
            self.control_number('1111-2222'), self.control_number('2222-4444'),
            self.control_number('4444-8888', 'Paragraph (b)(2) approved')])


class ExtractTagsTests(XMLBuilderMixin, TestCase):
    def setUp(self):
        super(ExtractTagsTests, self).setUp()
        self.et = preprocessors.ExtractTags()

    def test_extract_pair_not_pair(self):
        """XML shouldn't be modified and should get a negative response if
        this pattern isn't present"""
        with self.tree.builder("ROOT") as root:
            root.EXTRACT("contents")
            root.TAG1()

        with self.assert_xml_transformed() as original_xml:
            self.assertFalse(self.et.extract_pair(original_xml[0]))
            # No tree change

    def test_extract_pair_last_node(self):
        """XML shouldn't be modified when the EXTRACT is the last element"""
        with self.tree.builder("ROOT") as root:
            root.TAG1()
            root.EXTRACT("contents")

        with self.assert_xml_transformed() as original_xml:
            self.assertFalse(self.et.extract_pair(original_xml[1]))
            # No tree change

    def test_extract_pair(self):
        """Sequences of EXTRACT nodes should get joined"""
        with self.tree.builder("ROOT") as root:
            root.TAG1()
            root.EXTRACT("contents1")
            with root.EXTRACT("contents2") as extract:
                extract.TAG2()
                extract.TAG3()
            root.EXTRACT("contents3")
            root.TAG4()
            root.EXTRACT("contents4")

        contents = "contents1\ncontents2<TAG2/><TAG3/>"
        with self.assert_xml_transformed() as original_xml:
            self.assertTrue(self.et.extract_pair(original_xml[1]))
            with self.tree.builder("ROOT") as root:
                root.TAG1()
                root.EXTRACT(_xml=contents)
                root.EXTRACT("contents3")  # First pass will only merge one
                root.TAG4()
                root.EXTRACT("contents4")

        with self.assert_xml_transformed() as original_xml:
            self.assertTrue(self.et.extract_pair(original_xml[1]))
            contents += "\ncontents3"
            with self.tree.builder("ROOT") as root:
                root.TAG1()
                root.EXTRACT(_xml=contents)
                root.TAG4()
                root.EXTRACT("contents4")

    def test_sandwich_no_bread(self):
        """For sandwich to be triggered, EXTRACT tags need to be separated by
        only one tag"""
        with self.tree.builder("ROOT") as root:
            root.EXTRACT()
            root.GPOTABLE()
            root.GPOTABLE()
            root.EXTRACT()

        with self.assert_xml_transformed() as original_xml:
            self.assertFalse(self.et.sandwich(original_xml[0]))
            # No tree change

    def test_sandwich_last_tag(self):
        """For sandwich to be triggered, EXTRACT tag can't be the last tag"""
        with self.tree.builder("ROOT") as root:
            root.GPOTABLE()
            root.EXTRACT()

        with self.assert_xml_transformed() as original_xml:
            self.assertFalse(self.et.sandwich(original_xml[1]))
            # No tree change

    def test_sandwich_bad_filling(self):
        """For sandwich to be triggered, EXTRACT tags need to surround one of
        a handful of specific tags"""
        with self.tree.builder("ROOT") as root:
            root.EXTRACT()
            root.P()
            root.EXTRACT()

        with self.assert_xml_transformed() as original_xml:
            self.assertFalse(self.et.sandwich(original_xml[0]))
            # No tree change

    def test_sandwich(self):
        """When the correct tags are separated by EXTRACTs, they should get
        merged"""
        with self.tree.builder("ROOT") as root:
            root.TAG1()
            root.EXTRACT("extract contents")
            root.GPOTABLE("table contents")
            root.EXTRACT()

        with self.assert_xml_transformed() as original_xml:
            self.assertTrue(self.et.sandwich(original_xml[1]))
            with self.tree.builder("ROOT") as root:
                root.TAG1()
                contents = ("extract contents\n<GPOTABLE>table contents"
                            "</GPOTABLE>")
                root.EXTRACT(_xml=contents)
                root.EXTRACT()


class FootnotesTests(XMLBuilderMixin, TestCase):
    def setUp(self):
        super(FootnotesTests, self).setUp()
        self.fn = preprocessors.Footnotes()

    def test_split_comma_footnotes(self):
        """The XML will sometimes merge multiple references to footnotes into
        a single tag. Verify that they get split"""
        def ftnt_compare(original, expected):
            with self.tree.builder("ROOT") as root:
                root.P(_xml=original)

            with self.assert_xml_transformed() as original_xml:
                self.fn.split_comma_footnotes(original_xml)
                with self.tree.builder("ROOT") as root:
                    root.P(_xml=expected)

        ftnt_compare("Some content<SU>1</SU>.", "Some content<SU>1</SU>.")
        ftnt_compare("Some content<SU>1</SU>", "Some content<SU>1</SU>")
        ftnt_compare("More content<SU>2, 3, 4</SU>.",
                     "More content<SU>2</SU><SU>3</SU><SU>4</SU>.")
        ftnt_compare("No spaces<SU>2</SU><SU>3</SU><SU>4</SU>.",
                     "No spaces<SU>2</SU><SU>3</SU><SU>4</SU>.")
        ftnt_compare("Even more content<SU>2,3,4</SU>.",
                     "Even more content<SU>2</SU><SU>3</SU><SU>4</SU>.")
        ftnt_compare("""Newlines!<SU>2</SU>
                     <SU>3</SU>
                     <SU>4</SU>.""",
                     "Newlines!<SU>2</SU><SU>3</SU><SU>4</SU>.")
        ftnt_compare("""Newlines, commas!<SU>2</SU>,
                     <SU>3</SU>,
                     <SU>4</SU>.""",
                     "Newlines, commas!<SU>2</SU><SU>3</SU><SU>4</SU>.")
        ftnt_compare("Yet more <SU>2</SU>, whatever<SU>3, 4</SU>",
                     "Yet more <SU>2</SU>, whatever<SU>3</SU><SU>4</SU>")
        ftnt_compare("Penultimate content<SU>5 6</SU>",
                     "Penultimate content<SU>5</SU><SU>6</SU>")
        ftnt_compare("Last content<SU>7</SU>, <SU>8</SU>",
                     "Last content<SU>7</SU><SU>8</SU>")

    def test_add_ref_attributes(self):
        """The XML elements which reference footnotes should be modified to
        contain the contents of those footnotes"""
        with self.tree.builder("ROOT") as root:
            root.SU("1")
            root.SU("2")
            with root.FTNT() as ftnt:
                ftnt.P(_xml="<SU>1</SU> note for one")
            with root.TNOTE() as ftnt:
                ftnt.P(_xml="<SU>2</SU> note for two")

        with self.assert_xml_transformed() as original_xml:
            self.fn.add_ref_attributes(original_xml)
            with self.tree.builder("ROOT") as root:
                root.SU("1", footnote='note for one')
                root.SU("2", footnote='note for two')
                with root.FTNT() as ftnt:
                    ftnt.P(_xml="<SU>1</SU> note for one")
                with root.TNOTE() as ftnt:
                    ftnt.P(_xml="<SU>2</SU> note for two")

    def test_add_ref_attributes_missing(self):
        """SUs in different sections aren't related"""
        with self.tree.builder("ROOT") as root:
            with root.SECTION() as section:
                section.SU("1")
            with root.SECTION() as section:
                section.SU("1")
                with section.FTNT() as ftnt:
                    ftnt.P(_xml="<SU>1</SU> note for one")

        with self.assert_xml_transformed() as original_xml:
            self.fn.add_ref_attributes(original_xml)
            with self.tree.builder("ROOT") as root:
                with root.SECTION() as section:
                    section.SU("1")
                with root.SECTION() as section:
                    section.SU("1", footnote="note for one")
                    with section.FTNT() as ftnt:
                        ftnt.P(_xml="<SU>1</SU> note for one")
