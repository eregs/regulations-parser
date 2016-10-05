# -*- coding: utf-8 -*-
from unittest import TestCase

from lxml import etree
import pytest

from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser import preprocessors


class MoveLastAMDParTests(TestCase):
    def test_improper_amdpar_location(self):
        """The second AMDPAR is in the wrong parent; it should be moved"""
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT(ID="RT1"):
                ctx.AMDPAR(u"1. In § 105.1, revise paragraph (b):")
                with ctx.SECTION():
                    ctx.P("Some Content")
                # Note this has the wrong parent
                ctx.AMDPAR(u"3. In § 105.2, revise paragraph (a) to read:")
            with ctx.REGTEXT(ID="RT2"):
                with ctx.SECTION():
                    ctx.P("Other Content")

        preprocessors.MoveLastAMDPar().transform(ctx.xml)

        amd1, amd2 = ctx.xml.xpath("//AMDPAR")
        self.assertEqual(amd1.getparent().get("ID"), "RT1")
        self.assertEqual(amd2.getparent().get("ID"), "RT2")

    def test_trick_amdpar_location_diff_parts(self):
        """Similar situation to the above, except the regulations describe
        different parts and hence the AMDPAR should not move"""
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT(ID="RT1", PART="105"):
                ctx.AMDPAR(u"1. In § 105.1, revise paragraph (b):")
                with ctx.SECTION():
                    ctx.P("Some Content")
                ctx.AMDPAR(u"3. In § 105.2, revise paragraph (a) to read:")
            with ctx.REGTEXT(ID="RT2", PART="107"):
                with ctx.SECTION():
                    ctx.P("Other Content")

        preprocessors.MoveLastAMDPar().transform(ctx.xml)

        amd1, amd2 = ctx.xml.xpath("//AMDPAR")
        self.assertEqual(amd1.getparent().get("ID"), "RT1")
        self.assertEqual(amd2.getparent().get("ID"), "RT1")


class SupplementAMDParTests(TestCase):
    def test_incorrect_ps(self):
        """Supplement I AMDPARs are not always labeled as should be"""
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT():
                ctx.AMDPAR(u"1. In § 105.1, revise paragraph (b):")
                with ctx.SECTION():
                    ctx.STARS()
                    ctx.P("(b) Content")
                ctx.P("2. In Supplement I to Part 105,")
                ctx.P("A. Under Section 105.1, 1(b), paragraph 2 is revised")
                ctx.P("The revisions are as follows")
                ctx.HD("Supplement I to Part 105", SOURCE="HD1")
                ctx.STARS()
                with ctx.P():
                    ctx.E("1(b) Heading", T="03")
                ctx.STARS()
                ctx.P("2. New Context")

        preprocessors.SupplementAMDPar().transform(ctx.xml)

        # Note that the SECTION paragraphs were not converted
        self.assertEqual(
            [amd.text for amd in ctx.xml.xpath("//AMDPAR")],
            [u"1. In § 105.1, revise paragraph (b):",
             "2. In Supplement I to Part 105,",
             "A. Under Section 105.1, 1(b), paragraph 2 is revised",
             "The revisions are as follows"])


class ParenthesesCleanupTests(TestCase):
    def assert_transformed(self, original, new_text):
        """Helper function to verify that the XML is transformed as
        expected"""
        self.setUp()
        with XMLBuilder("PART") as ctx:
            ctx.child_from_string(u"<P>{}</P>".format(original))
        preprocessors.ParenthesesCleanup().transform(ctx.xml)
        self.assertEqual("<P>{}</P>".format(new_text),
                         etree.tounicode(ctx.xml[0]))

    def test_transform(self):
        """The parens should always move out"""
        expected = '(<E T="03">a</E>) Content'
        self.assert_transformed('(<E T="03">a</E>) Content', expected)
        self.assert_transformed('(<E T="03">a)</E> Content', expected)
        self.assert_transformed('<E T="03">(a</E>) Content', expected)
        self.assert_transformed('<E T="03">(a)</E> Content', expected)
        self.assert_transformed('<E T="03">Paragraph 22(a)(5)</E> Content',
                                '<E T="03">Paragraph 22(a)(5)</E> Content')


@pytest.mark.parametrize("input_xml,expected_xml", [
    (u'<E T="03">Things</E>— more things',
        u'<E T="03">Things—</E> more things'),
    ('<E T="03">Things</E>.', '<E T="03">Things.</E>'),
    ('<E T="03">Things</E>. more things', '<E T="03">Things.</E> more things'),
    ('<E T="03">Things</E>. more things.',
        '<E T="03">Things.</E> more things.'),
    ('<E T="03">Things</E>', '<E T="03">Things</E>'),
    ('<E T="03" />. Empty', '<E T="03">.</E> Empty')
])
def test_MoveAdjoiningChars_transform(input_xml, expected_xml):
    with XMLBuilder("SECTION") as ctx:
        ctx.child_from_string(u"<P>{}</P>".format(input_xml))
    preprocessors.MoveAdjoiningChars().transform(ctx.xml)
    assert etree.tounicode(ctx.xml.xpath('./P/E')[0]) == expected_xml


class ApprovalsFPTests(TestCase):
    def control_number(self, number, prefix="Approved"):
        return ("({} by the Office of Management and Budget under "
                "control number {})".format(prefix, number))

    def test_transform(self):
        """Verify that FP tags get transformed, but only if they match a
        certain string"""
        with XMLBuilder("PART") as ctx:
            ctx.APPRO(self.control_number('1111-2222'))
            ctx.FP("Something else")
            ctx.FP(self.control_number('2222-4444'))
            ctx.P(self.control_number('3333-6666'))
            with ctx.EXTRACT():
                ctx.FP(self.control_number(
                    "4444-8888", "Paragraph (b)(2) approved"))
            ctx.P(self.control_number('4444-8888'))
        preprocessors.ApprovalsFP().transform(ctx.xml)
        appros = [appro.text for appro in ctx.xml.xpath("./APPRO")]
        self.assertEqual(appros, [
            self.control_number('1111-2222'), self.control_number('2222-4444'),
            self.control_number('4444-8888', 'Paragraph (b)(2) approved')])


class ExtractTagsTests(TestCase):
    def setUp(self):
        super(ExtractTagsTests, self).setUp()
        self.et = preprocessors.ExtractTags()

    def test_extract_pair_not_pair(self):
        """XML shouldn't be modified and should get a negative response if
        this pattern isn't present"""
        with XMLBuilder("ROOT") as ctx:
            ctx.EXTRACT("contents")
            ctx.TAG1()
        original = ctx.xml_copy()

        self.assertFalse(self.et.extract_pair(ctx.xml[0]))
        self.assertEqual(ctx.xml_str, etree.tounicode(original))

    def test_extract_pair_last_node(self):
        """XML shouldn't be modified when the EXTRACT is the last element"""
        with XMLBuilder("ROOT") as ctx:
            ctx.TAG1()
            ctx.EXTRACT("contents")
        original = ctx.xml_copy()

        self.assertFalse(self.et.extract_pair(ctx.xml[1]))
        self.assertEqual(ctx.xml_str, etree.tounicode(original))

    def test_extract_pair(self):
        """Sequences of EXTRACT nodes should get joined"""
        with XMLBuilder("ROOT") as ctx:
            ctx.TAG1()
            ctx.EXTRACT("contents1")
            with ctx.EXTRACT("contents2"):
                ctx.TAG2()
                ctx.TAG3()
            ctx.EXTRACT("contents3")
            ctx.TAG4()
            ctx.EXTRACT("contents4")

        contents = "contents1\ncontents2<TAG2/><TAG3/>"
        with XMLBuilder("ROOT") as ctx2:
            ctx2.TAG1()
            ctx2.child_from_string('<EXTRACT>{}</EXTRACT>'.format(contents))
            ctx2.EXTRACT("contents3")  # First pass will only merge one
            ctx2.TAG4()
            ctx2.EXTRACT("contents4")
        self.assertTrue(self.et.extract_pair(ctx.xml[1]))
        self.assertEqual(ctx2.xml_str, ctx.xml_str)

        contents += "\ncontents3"
        with XMLBuilder("ROOT") as ctx3:
            ctx3.TAG1()
            ctx3.child_from_string('<EXTRACT>{}</EXTRACT>'.format(contents))
            ctx3.TAG4()
            ctx3.EXTRACT("contents4")
        self.assertTrue(self.et.extract_pair(ctx.xml[1]))
        self.assertEqual(ctx3.xml_str, ctx.xml_str)

    def test_sandwich_no_bread(self):
        """For sandwich to be triggered, EXTRACT tags need to be separated by
        only one tag"""
        with XMLBuilder("ROOT") as ctx:
            ctx.EXTRACT()
            ctx.GPOTABLE()
            ctx.GPOTABLE()
            ctx.EXTRACT()
        original = ctx.xml_copy()

        self.assertFalse(self.et.sandwich(ctx.xml[0]))
        self.assertEqual(ctx.xml_str, etree.tounicode(original))

    def test_sandwich_last_tag(self):
        """For sandwich to be triggered, EXTRACT tag can't be the last tag"""
        with XMLBuilder("ROOT") as ctx:
            ctx.GPOTABLE()
            ctx.EXTRACT()
        original = ctx.xml_copy()

        self.assertFalse(self.et.sandwich(ctx.xml[1]))
        self.assertEqual(ctx.xml_str, etree.tounicode(original))

    def test_sandwich_bad_filling(self):
        """For sandwich to be triggered, EXTRACT tags need to surround one of
        a handful of specific tags"""
        with XMLBuilder("ROOT") as ctx:
            ctx.EXTRACT()
            ctx.P()
            ctx.EXTRACT()
        original = ctx.xml_copy()

        self.assertFalse(self.et.sandwich(ctx.xml[0]))
        self.assertEqual(ctx.xml_str, etree.tounicode(original))

    def test_sandwich(self):
        """When the correct tags are separated by EXTRACTs, they should get
        merged"""
        with XMLBuilder("ROOT") as ctx:
            ctx.TAG1()
            ctx.EXTRACT("extract contents")
            ctx.GPOTABLE("table contents")
            ctx.EXTRACT()

        with XMLBuilder("ROOT") as ctx2:
            ctx2.TAG1()
            ctx2.child_from_string(
                '<EXTRACT>extract contents\n<GPOTABLE>table contents'
                '</GPOTABLE></EXTRACT>')
            ctx2.EXTRACT()
        self.assertTrue(self.et.sandwich(ctx.xml[1]))
        self.assertEqual(ctx.xml_str, ctx2.xml_str)


class FootnotesTests(TestCase):
    def setUp(self):
        super(FootnotesTests, self).setUp()
        self.fn = preprocessors.Footnotes()

    def test_split_comma_footnotes(self):
        """The XML will sometimes merge multiple references to footnotes into
        a single tag. Verify that they get split"""
        def ftnt_compare(original, expected):
            with XMLBuilder("ROOT") as ctx:
                ctx.child_from_string("<P>{}</P>".format(original))

            with XMLBuilder("ROOT") as ctx2:
                ctx2.child_from_string("<P>{}</P>".format(expected))
            self.fn.split_comma_footnotes(ctx.xml)
            self.assertEqual(ctx.xml_str, ctx2.xml_str)

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
        with XMLBuilder("ROOT") as ctx:
            ctx.SU("1")
            ctx.SU("2")
            with ctx.FTNT():
                ctx.child_from_string('<P><SU>1</SU> note for one</P>')
            with ctx.TNOTE():
                ctx.child_from_string('<P><SU>2</SU> note for two</P>')

        with XMLBuilder("ROOT") as ctx2:
            ctx2.SU("1", footnote='note for one')
            ctx2.SU("2", footnote='note for two')
            with ctx2.FTNT():
                ctx2.child_from_string('<P><SU>1</SU> note for one</P>')
            with ctx2.TNOTE():
                ctx2.child_from_string('<P><SU>2</SU> note for two</P>')

        self.fn.add_ref_attributes(ctx.xml)
        self.assertEqual(ctx.xml_str, ctx2.xml_str)

    def test_add_ref_attributes_missing(self):
        """SUs in different sections aren't related"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.SECTION():
                ctx.SU("1")
            with ctx.SECTION():
                ctx.SU("1")
                with ctx.FTNT():
                    ctx.child_from_string('<P><SU>1</SU> note for one</P>')

        with XMLBuilder("ROOT") as ctx2:
            with ctx2.SECTION():
                ctx2.SU("1")
            with ctx2.SECTION():
                ctx2.SU("1", footnote="note for one")
                with ctx2.FTNT():
                    ctx2.child_from_string('<P><SU>1</SU> note for one</P>')

        self.fn.add_ref_attributes(ctx.xml)
        self.assertEqual(ctx.xml_str, ctx2.xml_str)


class ParseAMDPARsTests(TestCase):
    def setUp(self):
        self.amdparser = preprocessors.ParseAMDPARs()

    def test_derives_part(self):
        """Associates the closest PART info when parsing AMDPARs"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT():
                ctx.AMDPAR("Revise section 14(a)")
            with ctx.REGTEXT(PART=1111):
                ctx.AMDPAR("Revise section 15(b)")
            with ctx.REGTEXT(PART=2222):
                ctx.AMDPAR("Revise section 16(c)")
            with ctx.REGTEXT():
                ctx.AMDPAR("Revise section 17(d)")
        self.amdparser.transform(ctx.xml)
        puts = ctx.xml.xpath('//AMDPAR/EREGS_INSTRUCTIONS/PUT')
        self.assertEqual(len(puts), 4)
        self.assertEqual(puts[0].get('label'), '1111-?-14-a')
        self.assertEqual(puts[1].get('label'), '1111-?-15-b')
        self.assertEqual(puts[2].get('label'), '2222-?-16-c')
        self.assertEqual(puts[3].get('label'), '2222-?-17-d')

    def test_dont_touch_manual(self):
        """Should not modify existing instructions"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(PART=111):
                with ctx.AMDPAR("Revise section 22(c)"):
                    with ctx.EREGS_INSTRUCTIONS():
                        # Completely unrelated to the AMDPAR
                        ctx.DELETE(label='222-?-5')
        original = ctx.xml_str
        self.amdparser.transform(ctx.xml)
        self.assertEqual(original, ctx.xml_str)

    def test_final_context(self):
        """The "final_context" attribute should be written"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(PART=111):
                ctx.AMDPAR("Remove section 2(b), revise section 3(c), add "
                           "section 4(d)(3)")
        self.amdparser.transform(ctx.xml)
        instructions = ctx.xml.xpath('//AMDPAR/EREGS_INSTRUCTIONS')
        self.assertEqual(1, len(instructions))
        self.assertEqual(instructions[0].get('final_context'), '111-?-4-d-3')


def test_replace_html_entities():
    xml_str = b"text <with field='&apos;'> But &rdquo; and &gt; + 2&cent;s"
    expected = u"text <with field='&apos;'> But ” and &gt; + 2¢s"
    expected = expected.encode('utf-8')
    assert preprocessors.replace_html_entities(xml_str) == expected
