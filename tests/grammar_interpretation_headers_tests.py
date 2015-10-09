from unittest import TestCase

from regparser.grammar import interpretation_headers as ih_lib


class GrammarInterpretationHeadersTest(TestCase):

    def test_par(self):
        match = ih_lib.parser.parseString("3(c)(4) Pandas")
        self.assertEqual('3', match.section)
        self.assertEqual('c', match.p1)
        self.assertEqual('4', match.p2)

    def test_section(self):
        match = ih_lib.parser.parseString("Section 105.11")
        self.assertEqual('105', match.part)
        self.assertEqual('11', match.section)

    def test_newline(self):
        starts = [start for _, start, _ in
                  ih_lib.parser.scanString("\nSection 100.22")]
        self.assertEqual(1, starts[0])
        starts = [start for _, start, _ in
                  ih_lib.parser.scanString("\nParagraph 2(b)(2)")]
        self.assertEqual(1, starts[0])

    def test_marker_par(self):
        match = ih_lib.parser.parseString("Paragraph 3(b)")
        self.assertEqual('3', match.section)
        self.assertEqual('b', match.p1)

    def test_appendix(self):
        match = ih_lib.parser.parseString("Appendix M - More Info")
        self.assertEqual('M', match.appendix)
