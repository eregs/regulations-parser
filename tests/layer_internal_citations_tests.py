# vim: set encoding=utf-8
from unittest import TestCase

from regparser.layer import internal_citations
from regparser.tree.struct import Node


class ParseTest(TestCase):
    def setUp(self):
        self.parser = internal_citations.InternalCitationParser(
            None, cfr_title=None)
        self.parser.verify_citations = False

    def test_process_method(self):
        node = Node("The requirements in paragraph (a)(4)(iii) of",
                    label=['1005', '6'])
        citations = self.parser.process(node)
        self.assertEqual(len(citations), 1)

    def test_underparagraph(self):
        text = 'Something something underparagraphs (a)(4) through (5)'
        citations = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(len(citations), 2)

    def test_except_for(self):
        text = 'paragraph (b)(2)(i) through (b)(2)(v) except for '
        text += '(b)(2)(i)(D) and (b)(2)(vii) through (b)(2)(xiv)'
        citations = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(len(citations), 5)
        self.assertEqual(citations[0]['citation'],
                         ['1005', '6', 'b', '2', 'i'])
        self.assertEqual(citations[1]['citation'],
                         ['1005', '6', 'b', '2', 'v'])
        self.assertEqual(citations[2]['citation'],
                         ['1005', '6', 'b', '2', 'i', 'D'])
        self.assertEqual(citations[3]['citation'],
                         ['1005', '6', 'b', '2', 'vii'])
        self.assertEqual(citations[4]['citation'],
                         ['1005', '6', 'b', '2', 'xiv'])

        text = 'paragraph (b)(2)(i) through (b)(2)(v) (except for '
        text += '(b)(2)(i)(D)) and (b)(2)(vii) through (b)(2)(xiv)'
        citations = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(len(citations), 5)
        self.assertEqual(citations[0]['citation'],
                         ['1005', '6', 'b', '2', 'i'])
        self.assertEqual(citations[1]['citation'],
                         ['1005', '6', 'b', '2', 'v'])
        self.assertEqual(citations[2]['citation'],
                         ['1005', '6', 'b', '2', 'i', 'D'])
        self.assertEqual(citations[3]['citation'],
                         ['1005', '6', 'b', '2', 'vii'])
        self.assertEqual(citations[4]['citation'],
                         ['1005', '6', 'b', '2', 'xiv'])

    def test_multiple_paragraphs(self):
        """ Ensure that offsets work correctly in a simple multiple paragraph
        scenario. """

        text = u"the requirements of paragraphs (c)(3), (d)(2), (e)(1), "
        text += "(e)(3), and (f) of this section"
        citations = self.parser.process(Node(text, label=['1005', '6']))

        self.assertEqual(len(citations), 5)

        for c in citations:
            if c['citation'] == ['1005', '6', u'c', u'3']:
                self.assertEqual(text[c['offsets'][0][0]], '(')
                self.assertEquals(c['offsets'], [(31, 37)])
                self.assertEquals(text[c['offsets'][0][0] + 1], 'c')
            if c['citation'] == ['1005', '6', u'd', u'2']:
                self.assertEquals(text[c['offsets'][0][0] + 1], 'd')

    def test_multiple_paragraph_or(self):
        """ Ensure that an 'or' between internal citations is matched
        correctly. """
        text = u"set forth in paragraphs (b)(1) or (b)(2)"
        citations = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEquals(2, len(citations))

    def test_single_paragraph(self):
        """ Ensure that offsets work correctly in a simple single paragraph
        citation. """
        text = 'The requirements in paragraph (a)(4)(iii) of'
        citations = self.parser.process(Node(text, label=['1005', '6']))
        c = citations[0]
        self.assertEquals(text[c['offsets'][0][0]:c['offsets'][0][1]],
                          u'(a)(4)(iii)')
        self.assertEquals(['1005', '6', 'a', '4', 'iii'], c['citation'])

    def test_single_labeled_paragraph(self):
        """ Ensure the parser doesn't pick up unecessary elements, such as the
        (a) in the text below. """
        text = '(a) Solicited issuance. Except as provided in paragraph (b) '
        text += 'of this section'
        citations = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(1, len(citations))

    def test_multiple_section_citation(self):
        """ Ensure that offsets work correctly in a simple multiple section
        citation case. """
        text = u"set forth in §§ 1005.6(b)(3) and 1005.11 (b)(1)(i) from 60 "
        text += "days"
        citations = self.parser.process(Node(text, label=['1005', '6']))

        self.assertEqual(len(citations), 2)
        occurrences = 0
        for c in citations:
            if c['citation'] == [u'1005', u'6', u'b', u'3']:
                occurrences += 1
                self.assertEquals(text[c['offsets'][0][0]:c['offsets'][0][1]],
                                  u'1005.6(b)(3)')
            if c['citation'] == [u'1005', u'11', u'b', u'1', u'i']:
                occurrences += 1
                self.assertEquals(text[c['offsets'][0][0]:c['offsets'][0][1]],
                                  u'1005.11 (b)(1)(i)')
        self.assertEquals(occurrences, 2)

    def test_single_section_citation(self):
        """ Ensure that offsets work correctly in a simple single section
        citation case. """
        text = u"date in § 1005.20(h)(1) must disclose"
        citations = self.parser.process(Node(text, label=['1005', '6']))
        c = citations[0]
        self.assertEquals(text[c['offsets'][0][0]:c['offsets'][0][1]],
                          u'1005.20(h)(1)')

    def test_multiple_paragraph_single_section(self):
        text = u'§ 1005.10(a) and (d)'
        result = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(2, len(result))
        self.assertEqual(['1005', '10', 'a'], result[0]['citation'])
        self.assertEqual(['1005', '10', 'd'], result[1]['citation'])
        start, end = result[0]['offsets'][0]
        self.assertEqual(u'1005.10(a)', text[start:end])
        start, end = result[1]['offsets'][0]
        self.assertEqual(u'(d)', text[start:end])

    def test_multiple_paragraph_single_section2(self):
        text = u'§ 1005.7(b)(1), (2) and (3)'
        result = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(3, len(result))
        self.assertEqual(['1005', '7', 'b', '1'], result[0]['citation'])
        self.assertEqual(['1005', '7', 'b', '2'], result[1]['citation'])
        self.assertEqual(['1005', '7', 'b', '3'], result[2]['citation'])
        start, end = result[0]['offsets'][0]
        self.assertEqual(u'1005.7(b)(1)', text[start:end])
        start, end = result[1]['offsets'][0]
        self.assertEqual(u'(2)', text[start:end])
        start, end = result[2]['offsets'][0]
        self.assertEqual(u'(3)', text[start:end])

    def test_multiple_paragraphs_this_section(self):
        text = u'paragraphs (c)(1) and (2) of this section'
        result = self.parser.process(Node(text, label=['1005', '6']))
        self.assertEqual(2, len(result))
        self.assertEqual(['1005', '6', 'c', '1'], result[0]['citation'])
        self.assertEqual(['1005', '6', 'c', '2'], result[1]['citation'])
        start, end = result[0]['offsets'][0]
        self.assertEqual(u'(c)(1)', text[start:end])
        start, end = result[1]['offsets'][0]
        self.assertEqual(u'(2)', text[start:end])

    def test_multiple_paragraphs_max_depth(self):
        text = u'see paragraphs (z)(9)(vi)(A) and (D)'
        results = self.parser.process(Node(text, label=['999', '88']))
        self.assertEqual(2, len(results))
        resultA, resultD = results
        self.assertEqual(['999', '88', 'z', '9', 'vi', 'A'],
                         resultA['citation'])
        offsets = resultA['offsets'][0]
        self.assertEqual('(z)(9)(vi)(A)', text[offsets[0]:offsets[1]])
        self.assertEqual(['999', '88', 'z', '9', 'vi', 'D'],
                         resultD['citation'])
        offsets = resultD['offsets'][0]
        self.assertEqual('(D)', text[offsets[0]:offsets[1]])

    def _assert_paragraphs(self, text, label, text_to_labels):
        """Given text to search, a node label, and a mapping between text in
        the original and citation labels, verify that the citations can be
        found in the text"""
        results = self.parser.process(Node(text, label=label))
        self.assertEqual(len(text_to_labels), len(results))
        for result in results:
            start, end = result['offsets'][0]
            key = text[start:end]
            self.assertEqual(text_to_labels[key], result['citation'])

    def test_multiple_paragraphs_alpha_then_roman(self):
        self._assert_paragraphs(
            'paragraphs (b)(1)(ii) and (iii)', ['1005', '6'],
            {'(b)(1)(ii)': ['1005', '6', 'b', '1', 'ii'],
             '(iii)': ['1005', '6', 'b', '1', 'iii']})
        self._assert_paragraphs(
            u'§ 1005.15(d)(1)(i) and (ii)', ['1005', '15'],
            {'1005.15(d)(1)(i)': ['1005', '15', 'd', '1', 'i'],
             '(ii)': ['1005', '15', 'd', '1', 'ii']})
        self._assert_paragraphs(
            u'§ 1005.9(a)(5) (i), (ii), or (iii)', ['1005', '9'],
            {'1005.9(a)(5) (i)': ['1005', '9', 'a', '5', 'i'],
             '(ii)': ['1005', '9', 'a', '5', 'ii'],
             '(iii)': ['1005', '9', 'a', '5', 'iii']})
        self._assert_paragraphs(
            u'§ 1005.11(a)(1)(vi) or (vii).', ['1005', '11'],
            {'1005.11(a)(1)(vi)': ['1005', '11', 'a', '1', 'vi'],
             '(vii)': ['1005', '11', 'a', '1', 'vii']})

    def test_appendix_citation(self):
        self._assert_paragraphs(
            "Please see A-5 and Q-2(r) and Z-12(g)(2)(ii) then more text",
            ['1005', '10'],
            {'A-5': ['1005', 'A', '5'],
             'Q-2(r)': ['1005', 'Q', '2(r)'],
             'Z-12(g)(2)(ii)': ['1005', 'Z', '12(g)(2)(ii)']})

    def test_section_verbose(self):
        self._assert_paragraphs(
            "And Section 222.87(d)(2)(i) says something", ['222', '87'],
            {'222.87(d)(2)(i)': ['222', '87', 'd', '2', 'i']})
        self._assert_paragraphs(
            "Listing sections 11.55(d) and 321.11 (h)(4)", ['222', '87'],
            {'11.55(d)': ['11', '55', 'd'],
             '321.11 (h)(4)': ['321', '11', 'h', '4']})

    def test_comment_header(self):
        self._assert_paragraphs(
            "See comment 32(b)(3) blah blah", ['222', '87'],
            {'32(b)(3)': ['222', '32', 'b', '3', Node.INTERP_MARK]})

    def test_sub_comment(self):
        self._assert_paragraphs(
            "refer to comment 36(a)(2)-3 of thing", ['222', '87'],
            {'36(a)(2)-3': ['222', '36', 'a', '2', Node.INTERP_MARK, '3']})
        self._assert_paragraphs(
            "See comment 3(b)(1)-1.v.", ['222', '87'],
            #   Note the final period is not included
            {'3(b)(1)-1.v': ['222', '3', 'b', '1', Node.INTERP_MARK, '1',
                             'v']})

    def test_multiple_comments(self):
        text = "See, e.g., comments 31(b)(1)(iv)-1 and 31(b)(1)(vi)-1"
        result = self.parser.process(Node(text, label=['222', '87']))
        self.assertEqual(2, len(result))
        self.assertEqual(['222', '31', 'b', '1', 'iv', Node.INTERP_MARK, '1'],
                         result[0]['citation'])
        offsets = result[0]['offsets'][0]
        self.assertEqual('31(b)(1)(iv)-1', text[offsets[0]:offsets[1]])
        self.assertEqual(['222', '31', 'b', '1', 'vi', Node.INTERP_MARK, '1'],
                         result[1]['citation'])
        offsets = result[1]['offsets'][0]
        self.assertEqual('31(b)(1)(vi)-1', text[offsets[0]:offsets[1]])

    def test_paren_in_interps(self):
        text = "covers everything except paragraph (d)(3)(i) of this section"
        result = self.parser.process(
            Node(text, label=['222', '87', Node.INTERP_MARK]))
        self.assertEqual(1, len(result))
        self.assertEqual(['222', '87', 'd', '3', 'i'], result[0]['citation'])
        offsets = result[0]['offsets'][0]
        self.assertEqual('(d)(3)(i)', text[offsets[0]:offsets[1]])

        result = self.parser.process(
            Node(text, label=['222', '87', 'd', '3', Node.INTERP_MARK]))
        self.assertEqual(1, len(result))
        self.assertEqual(['222', '87', 'd', '3', 'i'], result[0]['citation'])
        offsets = result[0]['offsets'][0]
        self.assertEqual('(d)(3)(i)', text[offsets[0]:offsets[1]])

    def test_cfr_format(self):
        """We aren't processing this form yet"""
        text = "12 CFR 1026.3(d)"
        result = self.parser.process(Node(text, label=['1111']))
        self.assertEqual(None, result)

    def test_verify_citations(self):
        tree = Node(label=['1111', '2', '3'],
                    children=[Node(label=['222', '1', '1']),
                              Node(label=['222', '1', '1'],
                                   children=[Node(label=['111', '34'])])])
        parser = internal_citations.InternalCitationParser(
            tree, cfr_title=None)
        parser.pre_process()
        self.assertEqual(parser.known_citations, {
            ('1111', '2', '3'), ('222', '1', '1'), ('111', '34')})

        parser.verify_citations = False
        text = 'Section 111.34 and paragraph (c)'
        result = parser.process(Node(text))
        self.assertEqual(2, len(result))

        parser.verify_citations = True
        result = parser.process(Node(text))
        self.assertEqual(1, len(result))
        start, end = result[0]['offsets'][0]
        self.assertEqual('111.34', text[start:end].strip())

    def test_internal_cfr_format(self):
        text = 'under 11 CFR 110.14 are not subject'
        self.parser.cfr_title = '11'
        result = self.parser.process(Node(text, label=['110', '1']))
        self.assertEqual(1, len(result))
        self.assertEqual(['110', '14'], result[0]['citation'])
        offsets = result[0]['offsets'][0]
        self.assertEqual('11 CFR 110.14', text[offsets[0]:offsets[1]])
        # Verify that CFR citations from other titles do not get caught.
        self.parser.cfr_title = '12'
        result = self.parser.process(Node(text, label=['110', '1']))
        self.assertEqual(None, result)
        # Verify that CFR citations from other parts do not get caught.
        self.parser.cfr_title = '11'
        result = self.parser.process(Node(text, label=['111', '1']))
        self.assertEqual(None, result)

    def test_multiple_internal_cfr(self):
        text = 'prohibited from making contributions under 11 CFR 110.19, '
        text += '110.20, and 110.21'
        self.parser.cfr_title = '11'
        result = self.parser.process(Node(text, label=['110', '1']))
        self.assertEqual(3, len(result))
        self.assertEqual(['110', '19'], result[0]['citation'])
        offsets = result[0]['offsets'][0]
        self.assertEqual('11 CFR 110.19', text[offsets[0]:offsets[1]])
        self.assertEqual(['110', '20'], result[1]['citation'])
        offsets = result[1]['offsets'][0]
        self.assertEqual('110.20', text[offsets[0]:offsets[1]])
        self.assertEqual(['110', '21'], result[2]['citation'])
        offsets = result[2]['offsets'][0]
        self.assertEqual('110.21', text[offsets[0]:offsets[1]])
