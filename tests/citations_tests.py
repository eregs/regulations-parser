# vim: set encoding=utf-8
from unittest import TestCase

from regparser.citations import Label, cfr_citations, internal_citations
from regparser.tree.struct import Node


def to_text(citation, original_text):
    return original_text[citation.start:citation.end].strip()


def to_full_text(citation, original_text):
    return original_text[citation.full_start:citation.full_end].strip()


class CitationsTest(TestCase):

    def test_interp_headers(self):
        for text, label in [
            ("Section 102.22Stuff", ['102', '22']),
            ("22(d) Content", ['101', '22', 'd']),
            ("22(d)(5) Content", ['101', '22', 'd', '5']),
            ("22(d)(5)(x) Content", ['101', '22', 'd', '5', 'x']),
            (u"§ 102.22(d)(5)(x) Content", ['102', '22', 'd', '5', 'x']),
            ("22(d)(5)(x)(Q) Content", ['101', '22', 'd', '5', 'x', 'Q']),
            ("Appendix A Heading", ['101', 'A']),
            ("Comment 21(c)-1 Heading", ['101', '21', 'c', 'Interp', '1']),
            ("Paragraph 38(l)(7)(i)(A)(2).",
                ['101', '38', 'l', '7', 'i', 'A', '2']),
            (u'Official Interpretations of § 102.33(c)(2)',
                ['102', '33', 'c', '2', 'Interp'])]:

            citations = internal_citations(text, Label(part='101'))
            self.assertEqual(1, len(citations))
            self.assertEqual(citations[0].label.to_list(), label)

    def test_single_references(self):
        for text, link, label in [
            ("The requirements in paragraph (a)(4)(iii) of",
             'paragraph (a)(4)(iii)', ['102', '6', 'a', '4', 'iii']),
            ("Creditors may comply with paragraphs (a)(6) of this section",
             'paragraphs (a)(6)', ['102', '6', 'a', '6']),
            (u"date in § 1005.20(h)(1) must disclose", u'§ 1005.20(h)(1)',
             ['1005', '20', 'h', '1']),
            ('(a) Solicited issuance. Except as provided in paragraph (b) ' +
             'of this section', 'paragraph (b)', ['102', '6', 'b']),
            ("And Section 222.87(d)(2)(i) says something",
             'Section 222.87(d)(2)(i)', ['222', '87', 'd', '2', 'i']),
            ("More in paragraph 22(a)(4).", "paragraph 22(a)(4)",
             ["102", "22", "a", "4"]),
            ("See comment 32(b)(3) blah blah", 'comment 32(b)(3)',
             ['102', '32', 'b', '3', 'Interp']),
            ("refer to comment 36(a)(2)-3 of thing", 'comment 36(a)(2)-3',
             ['102', '36', 'a', '2', 'Interp', '3']),
            ("See Appendix A-5", "Appendix A-5", ['102', 'A', '5']),
            ("See Appendix A-5(R)", "Appendix A-5(R)", ['102', 'A', '5(R)']),
            ("See comment 3(v)-1.v. Another", "comment 3(v)-1.v",
             ['102', '3', 'v', 'Interp', '1', 'v']),
            ("See the commentary to 3(b)(1)", 'commentary to 3(b)(1)',
             ['102', '3', 'b', '1', 'Interp']),
            ("See comment 3(b)(1)-1.v.", 'comment 3(b)(1)-1.v',
             ['102', '3', 'b', '1', 'Interp', '1', 'v']),
            ("See appendix G, part V.4.D.", 'appendix G, part V.4.D',
             ['102', 'G', 'V', '4', 'D']),
            ("See comment 3-1 for things", 'comment 3-1',
             ['102', '3', 'Interp', '1'])]:

            citations = internal_citations(text, Label(part='102',
                                                       section='6'))
            self.assertEqual(1, len(citations))
            citation = citations[0]
            self.assertEqual(citation.label.to_list(), label)
            self.assertEqual(link, to_full_text(citation, text))

    def test_single_reference_false_positives(self):
        text = "See the commentary. (a) child paragraph"
        citations = internal_citations(
            text, Label(part='102', section='1'))
        self.assertEqual(0, len(citations))

    def test_section_ref_in_appendix(self):
        text = u"""(a) Something something § 1005.7(b)(1)."""
        citations = internal_citations(
            text, Label(part='1005', appendix='A', appendix_section='2',
                        p1='a'))
        self.assertEqual(citations[0].label.to_list(),
                         ['1005', '7', 'b', '1'])

    def test_multiple_matches(self):
        text = "Please see A-5 and Q-2(r) and Z-12(g)(2)(ii) then more text"
        citations = internal_citations(text, Label(part='102', section='1'))
        self.assertEqual(3, len(citations))
        citation = citations[0]
        self.assertEqual(citation.label.to_list(), ['102', 'A', '5'])
        self.assertEqual(to_text(citation, text), 'A-5')
        citation = citations[1]
        self.assertEqual(citation.label.to_list(), ['102', 'Q', '2(r)'])
        self.assertEqual(to_text(citation, text), 'Q-2(r)')
        citation = citations[2]
        self.assertEqual(citation.label.to_list(),
                         ['102', 'Z', '12(g)(2)(ii)'])
        self.assertEqual(to_text(citation, text), 'Z-12(g)(2)(ii)')

        text = u"Appendices G and H—Yadda yadda"
        citations = internal_citations(text, Label(part='102'))
        self.assertEqual(2, len(citations))
        citG, citH = citations
        self.assertEqual(citG.label.to_list(), ['102', 'G'])
        self.assertEqual(citH.label.to_list(), ['102', 'H'])

    def test_single_match_multiple_paragraphs1(self):
        text = "the requirements of paragraphs (c)(3), (d)(2), (e)(1), "
        text += "(e)(3), and (f) of this section"
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(5, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '5', 'c', '3'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(c)(3)')
        citation = citations[1]
        self.assertEqual(['222', '5', 'd', '2'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(d)(2)')
        citation = citations[2]
        self.assertEqual(['222', '5', 'e', '1'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(e)(1)')
        citation = citations[3]
        self.assertEqual(['222', '5', 'e', '3'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(e)(3)')
        citation = citations[4]
        self.assertEqual(['222', '5', 'f'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(f)')

        text = "set forth in paragraphs (b)(1) or (b)(2)"
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '5', 'b', '1'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(b)(1)')
        citation = citations[1]
        self.assertEqual(['222', '5', 'b', '2'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(b)(2)')

        text = 'paragraphs (c)(1) and (2) of this section'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '5', 'c', '1'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(c)(1)')
        citation = citations[1]
        self.assertEqual(['222', '5', 'c', '2'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(2)')

        text = 'paragraphs (b)(1)(ii) and (iii)'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '5', 'b', '1', 'ii'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(b)(1)(ii)')
        citation = citations[1]
        self.assertEqual(['222', '5', 'b', '1', 'iii'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(iii)')

        text = 'see paragraphs (z)(9)(vi)(A) and (D)'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '5', 'z', '9', 'vi', 'A'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(z)(9)(vi)(A)')
        citation = citations[1]
        self.assertEqual(['222', '5', 'z', '9', 'vi', 'D'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(D)')

        text = 'see 32(d)(6) and (7) Content content'
        citations = internal_citations(text, Label(part='222'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '32', 'd', '6'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '32(d)(6)')
        citation = citations[1]
        self.assertEqual(['222', '32', 'd', '7'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(7)')

    def test_single_match_multiple_paragraphs2(self):
        text = u'§ 1005.10(a) and (d)'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['1005', '10', 'a'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '1005.10(a)')
        citation = citations[1]
        self.assertEqual(['1005', '10', 'd'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '(d)')

        text = u'§ 1005.7(b)(1), (2) and (3)'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(3, len(citations))
        self.assertEqual(['1005', '7', 'b', '1'],
                         citations[0].label.to_list())
        self.assertEqual(['1005', '7', 'b', '2'],
                         citations[1].label.to_list())
        self.assertEqual(['1005', '7', 'b', '3'],
                         citations[2].label.to_list())

        text = u'§ 1005.15(d)(1)(i) and (ii)'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        self.assertEqual(['1005', '15', 'd', '1', 'i'],
                         citations[0].label.to_list())
        self.assertEqual(['1005', '15', 'd', '1', 'ii'],
                         citations[1].label.to_list())

        text = u'§ 1005.9(a)(5) (i), (ii), or (iii)'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(3, len(citations))
        self.assertEqual(['1005', '9', 'a', '5', 'i'],
                         citations[0].label.to_list())
        self.assertEqual(['1005', '9', 'a', '5', 'ii'],
                         citations[1].label.to_list())
        self.assertEqual(['1005', '9', 'a', '5', 'iii'],
                         citations[2].label.to_list())

        text = u'§ 1005.11(a)(1)(vi) or (vii).'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        self.assertEqual(['1005', '11', 'a', '1', 'vi'],
                         citations[0].label.to_list())
        self.assertEqual(['1005', '11', 'a', '1', 'vii'],
                         citations[1].label.to_list())

        text = u'§§ 1005.3(b)(2) and (3), 1005.10(b), (d), and (e), 1005.13, '
        text += 'and 1005.20'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(7, len(citations))

        text = 'Sections 1005.3, .4, and .5'
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(3, len(citations))
        self.assertEqual(['1005', '3'], citations[0].label.to_list())
        self.assertEqual(['1005', '4'], citations[1].label.to_list())
        self.assertEqual(['1005', '5'], citations[2].label.to_list())

    def test_single_match_multiple_paragraphs4(self):
        text = "Listing sections 11.55(d) and 321.11 (h)(4)"
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['11', '55', 'd'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '11.55(d)')
        citation = citations[1]
        self.assertEqual(['321', '11', 'h', '4'], citation.label.to_list())
        self.assertEqual(to_text(citation, text), '321.11 (h)(4)')

    def test_single_match_multiple_paragraphs5(self):
        text = "See, e.g., comments 31(b)(1)(iv)-1 and 31(b)(1)(vi)-1"
        citations = internal_citations(text, Label(part='222', section='5'))
        self.assertEqual(2, len(citations))
        citation = citations[0]
        self.assertEqual(['222', '31', 'b', '1', 'iv', 'Interp', '1'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '31(b)(1)(iv)-1')
        citation = citations[1]
        self.assertEqual(['222', '31', 'b', '1', 'vi', 'Interp', '1'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '31(b)(1)(vi)-1')

    def test_single_match_multiple_paragraphs6(self):
        text = "comments 5(b)(3)-1 through -3"
        citations = internal_citations(text, Label(part='100', section='5'))
        citation = citations[0]
        self.assertEqual(2, len(citations))
        self.assertEqual(['100', '5', 'b', '3', 'Interp', '1'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '5(b)(3)-1')
        citation = citations[1]
        self.assertEqual(['100', '5', 'b', '3', 'Interp', '3'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '-3')

    def test_single_match_multiple_paragraphs7(self):
        text = "comments 5(b)(3)-1, 5(b)(3)-3, or 5(d)-1 through -3."
        citations = internal_citations(text, Label(part='100', section='5'))
        citation = citations[0]
        self.assertEqual(4, len(citations))
        self.assertEqual(['100', '5', 'b', '3', 'Interp', '1'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '5(b)(3)-1')
        citation = citations[1]
        self.assertEqual(['100', '5', 'b', '3', 'Interp', '3'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '5(b)(3)-3')
        citation = citations[2]
        self.assertEqual(['100', '5', 'd', 'Interp', '1'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '5(d)-1')
        citation = citations[3]
        self.assertEqual(['100', '5', 'd', 'Interp', '3'],
                         citation.label.to_list())
        self.assertEqual(to_text(citation, text), '-3')

    def test_single_match_multiple_paragraphs8(self):
        text = u'§ 105.2(a)(1)-(3)'
        citations = internal_citations(text, Label(part='100', section='2'))
        self.assertEqual(2, len(citations))

    def test_single_match_multiple_p_false_positives(self):
        text = "-9 text and stuff -2. (b) new thing"
        citations = internal_citations(text, Label(part='100', section='4'))
        self.assertEqual(0, len(citations))

    def test_cfr_citations_single(self):
        text = 'See 11 CFR 222.3(e)(3)(ii) for more'
        citations = cfr_citations(text)
        self.assertEqual(1, len(citations))
        self.assertEqual('11 CFR 222.3(e)(3)(ii)', to_text(citations[0], text))
        self.assertEqual(
            citations[0].label.settings,
            dict(cfr_title='11', part='222', section='3', p1='e', p2='3',
                 p3='ii'))

    def test_cfr_citations_single_no_section(self):
        """The "part" token can also be present; "section"s don't need to be"""
        text = 'See 11 CFR part 222 or 33 CFR 44'
        citations = cfr_citations(text)
        self.assertEqual(2, len(citations))
        c11, c33 = citations
        self.assertEqual('11 CFR part 222', to_text(c11, text))
        self.assertEqual('33 CFR 44', to_text(c33, text))
        self.assertEqual(c11.label.settings, dict(cfr_title='11', part='222'))
        self.assertEqual(c33.label.settings, dict(cfr_title='33', part='44'))

    def test_cfr_citations_multiple(self):
        text = 'Go look at 2 CFR 111.22, 333.45, and 444.55(e)'
        citations = cfr_citations(text)
        self.assertEqual(3, len(citations))

        self.assertEqual('2 CFR 111.22', to_text(citations[0], text))
        self.assertEqual(citations[0].label.settings,
                         dict(cfr_title='2', part='111', section='22'))

        self.assertEqual('333.45', to_text(citations[1], text))
        self.assertEqual(citations[1].label.settings,
                         dict(cfr_title='2', part='333', section='45'))

        self.assertEqual('444.55(e)', to_text(citations[2], text))
        self.assertEqual(
            citations[2].label.settings,
            dict(cfr_title='2', part='444', section='55', p1='e'))

    def test_cfr_citations_through(self):
        text = u'See 27 CFR 479.112, 479.114 – 479.119'
        citations = cfr_citations(text)
        self.assertEqual(3, len(citations))
        twelve, fourteen, nineteen = citations

        self.assertEqual('27 CFR 479.112', to_text(twelve, text))
        self.assertEqual(twelve.label.settings,
                         dict(cfr_title='27', part='479', section='112'))
        self.assertEqual('479.114', to_text(fourteen, text))
        self.assertEqual(fourteen.label.settings,
                         dict(cfr_title='27', part='479', section='114'))
        self.assertEqual('479.119', to_text(nineteen, text))
        self.assertEqual(nineteen.label.settings,
                         dict(cfr_title='27', part='479', section='119'))

        citations = cfr_citations(text, include_fill=True)
        self.assertEqual(
            [citation.label.settings for citation in citations],
            [dict(cfr_title='27', part='479', section=str(i))
             for i in (112, 114, 115, 116, 117, 118, 119)])


class CitationsLabelTest(TestCase):
    def test_using_default_schema(self):
        label = Label(part='111')
        self.assertTrue(label.using_default_schema)
        label = Label(part='111', p1='b')
        self.assertTrue(label.using_default_schema)
        label = Label(part='111', c2='r')
        self.assertTrue(label.using_default_schema)

        label = Label(part='111', section='21')
        self.assertFalse(label.using_default_schema)
        label = Label(part='111', appendix='B3')
        self.assertFalse(label.using_default_schema)
        label = Label(part='111', appendix_section='3')
        self.assertFalse(label.using_default_schema)

    def test_determine_schema(self):
        self.assertEqual(Label.app_sect_schema,
                         Label.determine_schema({'appendix_section': '1'}))
        self.assertEqual(Label.app_schema,
                         Label.determine_schema({'appendix': 'A'}))
        self.assertEqual(Label.regtext_schema,
                         Label.determine_schema({'section': '12'}))
        self.assertEqual(None, Label.determine_schema({}))

    def test_to_list(self):
        label = Label(part='222', section='11', p1='c', p2='2')
        self.assertEqual(['222', '11', 'c', '2'], label.to_list())

        label = Label(part='222', p1='d', appendix='R3')
        self.assertEqual(['222', 'R3', 'd'], label.to_list())

        label = Label(part='222', p1='d', appendix='R', appendix_section='4')
        self.assertEqual(['222', 'R', '4', 'd'], label.to_list())

    def test_copy(self):
        label = Label(part='222', section='11', p1='c', p2='2')
        label = label.copy(p3='ii')
        self.assertEqual(['222', '11', 'c', '2', 'ii'], label.to_list())

        label = label.copy(p2='4', p3='iv')
        self.assertEqual(['222', '11', 'c', '4', 'iv'], label.to_list())

        label = label.copy(section='12', p1='d')
        self.assertEqual(['222', '12', 'd'], label.to_list())

        label = label.copy(appendix='D', appendix_section='4')
        self.assertEqual(['222', 'D', '4'], label.to_list())

        label = label.copy(p1='c', p2='3')
        self.assertEqual(['222', 'D', '4', 'c', '3'], label.to_list())

    def test_from_node(self):
        for lst, typ in [(['111'], Node.REGTEXT),
                         (['111', '31', 'a', '3'], Node.REGTEXT),
                         # _Very_ deeply nested, ignoring the recommended
                         # 6-level paragraph limit
                         (['111', '2', 'c', '4', 'v', 'F', '7', 'viii',
                           'p1', 'p1', 'p1'], Node.REGTEXT),
                         (['111', 'A', 'b'], Node.APPENDIX),
                         (['111', 'A', '4', 'a'], Node.APPENDIX),
                         (['111', '21', 'Interp'], Node.INTERP),
                         (['111', '21', 'Interp', '1'], Node.INTERP),
                         (['111', '21', 'r', 'Interp'], Node.INTERP),
                         (['111', '21', 'r', 'Interp', '2'], Node.INTERP),
                         (['111', 'G', 'Interp'], Node.INTERP),
                         (['111', 'G3', 'r', 'Interp'], Node.INTERP),
                         (['111', 'G', '2', 'Interp'], Node.INTERP),
                         (['111', 'G3', 'r', 'Interp', '3'], Node.INTERP),
                         (['111', 'G', '2', 'Interp', '5'], Node.INTERP),
                         (['111', 'Subpart', 'A'], Node.SUBPART),
                         (['111', 'Subpart'], Node.EMPTYPART)]:
            n = Node(label=lst, node_type=typ)
            self.assertEqual(Label.from_node(n).to_list(), lst)

    def test_label_representation(self):
        l = Label(part='105', section='3')
        self.assertEqual(
            repr(l),
            "Label(cfr_title=None, part='105', section='3', p1=None, "
            "p2=None, p3=None, p4=None, p5=None, p6=None, p7=None, p8=None, "
            "p9=None)")

    def test_lt(self):
        """Comparisons between labels"""
        self.assertTrue(Label(part='105', section='3') <
                        Label(part='105', section='4'))
        self.assertTrue(Label(part='105', section='3') <
                        Label(part='105', section='3', p1='a'))
        self.assertTrue(Label(part='105', section='3', p1='a') <
                        Label(part='222'))

    def test_labels_until_paragraphs(self):
        """We can fill in paragraphs"""
        start = Label(cfr_title='11', part='222', section='33', p1='a', p2='2')
        end = Label(cfr_title='11', part='222', section='33', p1='a', p2='6')
        self.assertEqual(
            list(start.labels_until(end)),
            [Label(cfr_title='11', part='222', section='33', p1='a', p2='3'),
             Label(cfr_title='11', part='222', section='33', p1='a', p2='4'),
             Label(cfr_title='11', part='222', section='33', p1='a', p2='5')])

    def test_labels_until_sections(self):
        """We can fill in sections"""
        start = Label(cfr_title='11', part='222', section='33')
        end = Label(cfr_title='11', part='222', section='36')
        self.assertEqual(list(start.labels_until(end)),
                         [Label(cfr_title='11', part='222', section='34'),
                          Label(cfr_title='11', part='222', section='35')])

    def assert_empty_until(self, start, end):
        """Shorthand method"""
        self.assertEqual([], list(start.labels_until(end)))

    def test_labels_until_fail(self):
        """We can't always fill in labels"""
        start = Label(part='111', section='22', p1='c')
        self.assert_empty_until(start, Label(part='111', section='23'))
        self.assert_empty_until(start, Label(part='111', section='22', p1='4'))
        self.assert_empty_until(start, Label(part='111', appendix='A', p1='3'))
