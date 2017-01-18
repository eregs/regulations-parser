# -*- coding: utf-8 -*-
from unittest import TestCase

from six.moves.html_parser import HTMLParser

from regparser.grammar import unified


class GrammarCommonTests(TestCase):

    def test_depth1_p(self):
        text = '(c)(2)(ii)(A)(<E T="03">2</E>)'
        result = unified.depth1_p.parseString(text)
        self.assertEqual('c', result.p1)
        self.assertEqual('2', result.p2)
        self.assertEqual('ii', result.p3)
        self.assertEqual('A', result.p4)
        self.assertEqual('2', result.p5)

    def test_marker_subpart_title(self):
        # Typical case:
        text = u'Subpart K\u2014Exportation'
        result = unified.marker_subpart_title.parseString(text)
        self.assertEqual(u'Exportation', result.subpart_title)
        self.assertEqual(u'K', result.subpart)

        # Reserved subpart:
        text = u'Subpart J [Reserved]'
        result = unified.marker_subpart_title.parseString(text)
        self.assertEqual(u'[Reserved]', result.subpart_title)
        self.assertEqual(u'J', result.subpart)

    def test_marker_comment(self):
        texts = [u'comment § 1004.3-4-i',
                 u'comment § 1004.3-4.i',
                 u'comment 1004.3-4-i',
                 u'comment 1004.3-4.i',
                 u'comment 3-4-i']
        for t in texts:
            result = unified.marker_comment.parseString(t)
            self.assertEqual("3", result.section)
            self.assertEqual("4", result.c1)

    def assert_notice_cfr_p_match(self, text, title, parts):
        result = unified.notice_cfr_p.parseString(text)
        self.assertEqual(str(title), result.cfr_title)
        self.assertEqual([str(part) for part in parts], list(result.cfr_parts))

    def test_notice_cfr_p(self):
        self.assert_notice_cfr_p_match('12 CFR Parts 1002, 1024, and 1026',
                                       title=12, parts=[1002, 1024, 1026])
        self.assert_notice_cfr_p_match('12 CFR Parts 1024, and 1026',
                                       title=12, parts=[1024, 1026])
        self.assert_notice_cfr_p_match('12 CFR Parts 1024',
                                       title=12, parts=[1024])
        self.assert_notice_cfr_p_match('12 CFR 1024', title=12, parts=[1024])

    def _decode(self, txt):
        """Convert from HTML entities"""
        return HTMLParser().unescape(txt)

    def test_whitespace(self):
        """Verify that various types of whitespace are ignored"""
        for whitespace in (" ", "\n", "\t", self._decode(u'&#8201;')):
            text = u'§{0}478.39a'.format(whitespace)
            result = unified.marker_part_section.parseString(text)
            self.assertEqual("478", result.part)
            self.assertEqual("39a", result.section)
