#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from unittest import TestCase

from lxml import etree
from regparser.layer import formatting
from regparser.tree.struct import Node
from tests.xml_builder import XMLBuilderMixin
from regparser.tree.xml_parser import preprocessors


class LayerFormattingTests(XMLBuilderMixin, TestCase):
    def test_build_header(self):
        """
        I think this header is supposed to look like this:


        |1-1|1-2                    |
        |   |2-1        |2-2        |
        |   |3-1|3-2|3-3|3-4|3-5|3-6|

        """
        with self.tree.builder("BOXHD") as root:
            root.CHED("1-1", H=1)
            root.CHED("1-2", H=1)
            root.CHED("2-1", H=2)
            root.CHED("3-1", H=3)
            root.CHED("3-2", H=3)
            root.CHED("3-3", H=3)
            root.CHED("2-2", H=2)
            root.CHED("3-4", H=3)
            root.CHED("3-5", H=3)
            root.CHED(_xml="3-6<LI>Other Content</LI>", H=3)
        root = formatting.build_header(self.tree.render_xml().xpath('./CHED'))

        n11, n12 = root.children
        self.assertEqual('1-1', n11.text)
        self.assertEqual(1, n11.colspan)
        self.assertEqual(3, n11.rowspan)
        self.assertEqual([], n11.children)

        self.assertEqual('1-2', n12.text)
        self.assertEqual(6, n12.colspan)
        self.assertEqual(1, n12.rowspan)

        n21, n22 = n12.children
        self.assertEqual('2-1', n21.text)
        self.assertEqual(3, n21.colspan)
        self.assertEqual(1, n21.rowspan)

        n31, n32, n33 = n21.children
        self.assertEqual('3-1', n31.text)
        self.assertEqual('3-2', n32.text)
        self.assertEqual('3-3', n33.text)
        for n in n21.children:
            self.assertEqual(1, n.colspan)
            self.assertEqual(1, n.rowspan)

        self.assertEqual('2-2', n22.text)
        self.assertEqual(3, n22.colspan)
        self.assertEqual(1, n22.rowspan)

        n34, n35, n36 = n22.children
        self.assertEqual('3-4', n34.text)
        self.assertEqual('3-5', n35.text)
        self.assertEqual('3-6 Other Content', n36.text)
        for n in n22.children:
            self.assertEqual(1, n.colspan)
            self.assertEqual(1, n.rowspan)

    def test_process_table(self):
        with self.tree.builder("GPOTABLE") as root:
            with root.BOXHD() as hd:
                hd.CHED("1-1", H=1)
                hd.CHED("1-2", H=1)
                hd.CHED("2-1", H=2)
                hd.CHED("3-1", H=3)
                hd.CHED("2-2", H=2)
                hd.CHED("3-2", H=3)
                hd.CHED(_xml="3-3<LI>Content</LI>Here", H=3)
            with root.ROW() as row:
                row.ENT("11")
                row.ENT("12")
                row.ENT("13")
                row.ENT("14")
            with root.ROW() as row:
                row.ENT("21")
                row.ENT("22")
                row.ENT("23")
            with root.ROW() as row:
                row.ENT()
                row.ENT("32")
                row.ENT(_xml="33<E>More</E>")
                row.ENT("34")
        xml = self.tree.render_xml()
        markdown = formatting.table_xml_to_plaintext(xml)
        self.assertTrue("3-3 Content Here" in markdown)
        self.assertTrue("33 More" in markdown)
        node = Node(markdown, source_xml=xml)
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]

        self.assertEqual(markdown, result['text'])
        self.assertEqual([0], result['locations'])

        mkhd = lambda t, c, r: {'text': t, 'colspan': c, 'rowspan': r}
        data = result['table_data']
        self.assertEqual(
            data['header'],
            [[mkhd('1-1', 1, 3), mkhd('1-2', 3, 1)],
             [mkhd('2-1', 1, 1), mkhd('2-2', 2, 1)],
             [mkhd('3-1', 1, 1), mkhd('3-2', 1, 1),
              mkhd('3-3 Content Here', 1, 1)]])
        self.assertEqual(
            data['rows'],
            [['11', '12', '13', '14'],
             ['21', '22', '23'],
             ['', '32', '33 More', '34']])

    def test_table_with_caption_as_caption(self):
        """
         Caption
        |R1C1     |
        |R2C1|R2C2|
        """
        with self.tree.builder("GPOTABLE", COLS="6") as root:
            root.TTITLE("Caption")
            with root.BOXHD() as hd:
                hd.CHED(u"R1C1", H=1)
                hd.CHED(u"R2C1", H=2)
                hd.CHED(u"R2C2", H=2)

        xml = self.tree.render_xml()
        markdown = formatting.table_xml_to_plaintext(xml)
        self.assertTrue("R1C1" in markdown)
        self.assertTrue("R2C2" in markdown)

        node = Node(markdown, source_xml=xml)
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]

        self.assertEqual(markdown, result['text'])
        self.assertEqual([0], result['locations'])
        data = result['table_data']
        self.assertTrue("header" in data)
        # Verify header matches:
        mkhd = lambda t, c, r: {'text': t, 'colspan': c, 'rowspan': r}
        self.assertEqual(
            [
                [mkhd("R1C1", 2, 1)],
                [mkhd("R2C1", 1, 1), mkhd("R2C2", 1, 1)]
            ],
            data["header"])
        self.assertTrue("caption" in data)
        self.assertEqual("Caption", data["caption"])

    def test_table_with_header_with_footnotes(self):
        """

        |R1C1[^1] |
        |R2C1|R2C2|
        """
        with self.tree.builder("GPOTABLE", COLS="6") as root:
            with root.BOXHD() as hd:
                hd.CHED(_xml=u"R1C1<SU>1</SU>", H=1)
                hd.CHED(u"R2C1", H=2)
                hd.CHED(u"R2C2", H=2)
            root.TNOTE(
                _xml="<SU>1</SU> No work of any kind shall be conducted")

        preprocessor = preprocessors.Footnotes()
        xml = self.tree.render_xml()
        preprocessor.transform(xml)
        markdown = formatting.table_xml_to_plaintext(xml)
        self.assertTrue("R1C1" in markdown)
        self.assertTrue("R2C2" in markdown)

        node = Node(markdown, source_xml=xml)
        result = formatting.Formatting(None).process(node)
        self.assertEqual(2, len(result))
        table, footnote = result

        self.assertEqual(markdown, table['text'])
        self.assertEqual([0], table['locations'])
        data = table['table_data']
        self.assertTrue("header" in data)
        # Verify header matches:
        mkhd = lambda t, c, r: {'text': t, 'colspan': c, 'rowspan': r}
        self.assertEqual(
            [
                [mkhd("R1C1[^1](No work of any kind shall be conducted)",
                      2, 1)],
                [mkhd("R2C1", 1, 1), mkhd("R2C2", 1, 1)]
            ],
            data["header"])
        self.assertEqual(u'[^1](No work of any kind shall be conducted)',
                         footnote['text'])
        self.assertEqual(u'1', footnote['footnote_data']['ref'])
        self.assertEqual(u'No work of any kind shall be conducted',
                         footnote['footnote_data']['note'])
        self.assertEqual([0], footnote['locations'])

    def test_table_with_caption_with_footnote_as_caption(self):
        """
        Caption[^1](No work of any kind shall be conducted)
         Caption[^1]
        |R1C1       |
        |R2C1 |R2C2 |

        This is testing the implementation of the TTITLE as a caption element.
        """
        with self.tree.builder("GPOTABLE", COLS="6") as root:
            root.TTITLE(_xml="Caption<SU>1</SU>")
            with root.BOXHD() as hd:
                hd.CHED(u"R1C1", H=1)
                hd.CHED(u"R2C1", H=2)
                hd.CHED(u"R2C2", H=2)
            root.TNOTE(
                _xml="<SU>1</SU> No work of any kind shall be conducted")

        preprocessor = preprocessors.Footnotes()
        xml = self.tree.render_xml()
        preprocessor.transform(xml)
        markdown = formatting.table_xml_to_plaintext(xml)
        self.assertTrue("R1C1" in markdown)
        self.assertTrue("R2C2" in markdown)

        node = Node(markdown, source_xml=xml)
        result = formatting.Formatting(None).process(node)
        self.assertEqual(2, len(result))
        table, footnote = result

        self.assertEqual(markdown, table['text'])
        self.assertEqual([0], table['locations'])
        data = table['table_data']
        self.assertTrue("header" in data)
        # Verify header matches:
        mkhd = lambda t, c, r: {'text': t, 'colspan': c, 'rowspan': r}
        self.assertEqual(
            [
                [mkhd("R1C1", 2, 1)],
                [mkhd("R2C1", 1, 1), mkhd("R2C2", 1, 1)]
            ],
            data["header"])
        self.assertTrue("caption" in data)
        self.assertEqual("Caption[^1](No work of any kind shall be conducted)",
                         data["caption"])
        self.assertEqual(u'[^1](No work of any kind shall be conducted)',
                         footnote['text'])
        self.assertEqual(u'1', footnote['footnote_data']['ref'])
        self.assertEqual(u'No work of any kind shall be conducted',
                         footnote['footnote_data']['note'])
        self.assertEqual([0], footnote['locations'])

    def test_awkward_table(self):
        """
        |R1C1     |R1C2               |
        |R2C1|R2C2|R2C3     |R2C4     |
        |    |    |R3C1|R3C2|R3C3|R3C4|
        """
        with self.tree.builder("GPOTABLE", COLS="6") as root:
            with root.BOXHD() as hd:
                hd.CHED(u"R1C1", H=1)
                hd.CHED(u"R2C1", H=2)
                hd.CHED(u"R2C2", H=2)
                hd.CHED(u"R1C2", H=1)
                hd.CHED(u"R2C3", H=2)
                hd.CHED(u"R3C1", H=3)
                hd.CHED(u"R3C2", H=3)
                hd.CHED(u"R2C4", H=2)
                hd.CHED(u"R3C3", H=3)
                hd.CHED(u"R3C4", H=3)

        xml = self.tree.render_xml()
        markdown = formatting.table_xml_to_plaintext(xml)
        self.assertTrue("R1C1" in markdown)
        self.assertTrue("R2C2" in markdown)

        node = Node(markdown, source_xml=xml)
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]

        self.assertEqual(markdown, result['text'])
        self.assertEqual([0], result['locations'])
        data = result['table_data']
        self.assertTrue("header" in data)
        # Verify header matches:
        mkhd = lambda t, c, r: {'text': t, 'colspan': c, 'rowspan': r}
        self.assertEqual(
            data["header"],
            [
                [mkhd("R1C1", 2, 1), mkhd("R1C2", 4, 1)],
                [mkhd("R2C1", 1, 2), mkhd("R2C2", 1, 2), mkhd("R2C3", 2, 1),
                    mkhd("R2C4", 2, 1)],
                [mkhd("R3C1", 1, 1), mkhd("R3C2", 1, 1), mkhd("R3C3", 1, 1),
                    mkhd("R3C4", 1, 1)]
            ])

    def test_atf_555_218_table(self):
        """
        Inspired by the more complicated table headers from ATF 27 555.

        This is a difficult table, 555.218; it should look something like this:

        |Q of expl  |Distances in feet                                        |
        |lbs >|lbs <|Inhb bldgs|hwys <3000 veh|hwys >3000 veh|sep magazines   |
        |     |     |Barr|Unbar|Barr  |Unbar  |Barr  |Unbar  |Barr   |Unbarr  |
        |-----|-----|----|-----|------|-------|------|-------|-------|--------|
        |1    |2    |3   |4    |5     |6      |7     |8      |9      |10      |

        """
        xml = etree.fromstring("""
            <GPOTABLE CDEF="7,7,5,5,5,5,6,6,5,5" COLS="10" OPTS="L2">
              <BOXHD>
                <CHED H="1">Quantity of explosives</CHED>
                <CHED H="2">Pounds over</CHED>
                <CHED H="2">Pounds not over</CHED>
                <CHED H="1">Distances in feet</CHED>
                <CHED H="2">Inhabited buildings</CHED>
                <CHED H="3">Barri-caded</CHED>
                <CHED H="3">Unbarri-caded</CHED>
                <CHED H="2">Public highways with traffic volume of 3000</CHED>
                <CHED H="3">Barri-caded</CHED>
                <CHED H="3">Unbarri-caded</CHED>
                <CHED H="2">Passenger railways—public highways</CHED>
                <CHED H="3">Barri-caded</CHED>
                <CHED H="3">Unbarri-caded</CHED>
                <CHED H="2">Separation of magazines</CHED>
                <CHED H="3">Barri-caded</CHED>
                <CHED H="3">Unbarri-caded</CHED>
              </BOXHD>
              <ROW>
                <ENT I="01">0</ENT>
                <ENT>5</ENT>
                <ENT>70</ENT>
                <ENT>140</ENT>
                <ENT>30</ENT>
                <ENT>60</ENT>
                <ENT>51</ENT>
                <ENT>102</ENT>
                <ENT>6</ENT>
                <ENT>12</ENT>
              </ROW>
            </GPOTABLE>""")
        markdown = formatting.table_xml_to_plaintext(xml)
        self.assertTrue("Quantity of explosives" in markdown)
        self.assertTrue("public highways" in markdown)

        node = Node(markdown, source_xml=xml)
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]

        self.assertEqual(markdown, result['text'])
        self.assertEqual([0], result['locations'])
        data = result['table_data']
        self.assertTrue("header" in data)
        # Verify header matches:
        mkhd = lambda t, c, r: {'text': t, 'colspan': c, 'rowspan': r}
        hwys_header = mkhd("Public highways with traffic volume of 3000",
                           2, 1)
        rail_header = mkhd(u"Passenger railways—public highways",
                           2, 1)
        barr_header = mkhd(u"Barri-caded", 1, 1)
        unbr_header = mkhd(u"Unbarri-caded", 1, 1)
        self.assertEqual(
            data["header"],
            [
                [mkhd("Quantity of explosives", 2, 1),
                 mkhd("Distances in feet", 8, 1)],
                [mkhd("Pounds over", 1, 2), mkhd("Pounds not over", 1, 2),
                 mkhd("Inhabited buildings", 2, 1), hwys_header, rail_header,
                 mkhd("Separation of magazines", 2, 1)],
                [barr_header, unbr_header, barr_header, unbr_header,
                 barr_header, unbr_header, barr_header, unbr_header]
            ])


class FencedTests(TestCase):
    def test_process(self):
        text = "Content content\n```abc def\nLine 1\nLine 2\n```"
        result = list(formatting.FencedData().process(text))
        self.assertEqual(1, len(result))
        result = result[0]
        self.assertEqual(result['text'], text[16:])
        self.assertEqual(result['fence_data'],
                         {'type': 'abc def', 'lines': ['Line 1', 'Line 2']})


class SubscriptTests(TestCase):
    def test_process(self):
        text = "This is a_{subscript}. And then a_{subscript} again"
        result = list(formatting.Subscript().process(text))
        self.assertEqual(1, len(result))
        result = result[0]
        self.assertEqual(
            result, {'text': '_{subscript}', 'locations': [0, 1],
                     'subscript_data': {'subscript': 'subscript'}})

    def test_process_parens(self):
        """Example from 27 CFR 555.180(d)(3)(ii)"""
        text = ("(ii) 2,3-Dimethyl-2,3-dinitrobutane (DMNB), C_{6} H_{12} "
                "(NO_{2})_{2}, molecular weight 176, when the minimum "
                "concentration in the finished explosive is 0.1 percent by "
                "mass;")
        result = list(formatting.Subscript().process(text))
        self.assertEqual(3, len(result))
        twelve, two, six = sorted(result, key=lambda d: d['text'])
        self.assertEqual(six, {'text': '_{6}', 'locations': [0],
                               'subscript_data': {'subscript': '6'}})
        self.assertEqual(twelve, {'text': '_{12}', 'locations': [0],
                                  'subscript_data': {'subscript': '12'}})
        self.assertEqual(two, {'text': '_{2}', 'locations': [0, 1],
                               'subscript_data': {'subscript': '2'}})


class SuperscriptTests(TestCase):
    def test_process(self):
        text = "This is a^{superscript}. And then another^{superscript} again"
        result = list(formatting.Superscript().process(text))
        self.assertEqual(1, len(result))
        result = result[0]
        self.assertEqual(
            result, {'text': '^{superscript}', 'locations': [0, 1],
                     'superscript_data': {'superscript': 'superscript'}})

    def test_process_emdash(self):
        text = u"This is an^{−emdash}"
        result = list(formatting.Superscript().process(text))
        self.assertEqual(1, len(result))
        result = result[0]
        self.assertEqual(
            result, {'text': u'^{−emdash}', 'locations': [0],
                     'superscript_data': {'superscript': u'−emdash'}})


class DashesTests(TestCase):
    def test_process(self):
        text = "This is an fp-dash_____"
        result = list(formatting.Dashes().process(text))
        self.assertEqual(1, len(result))
        result = result[0]

        self.assertEqual(result['text'], "This is an fp-dash_____")
        self.assertEqual(result['locations'], [0])
        self.assertEqual(result['dash_data'],
                         {'text': 'This is an fp-dash'})


class FootnotesTests(TestCase):
    def test_process_simple(self):
        text = "Something like[^1](where 'like' is not defined) this"
        result = list(formatting.Footnotes().process(text))
        self.assertEqual(result, [{
            'text': text[len("Something like"):-len(" this")],
            'locations': [0],
            'footnote_data': {'ref': '1',
                              'note': "where 'like' is not defined"}}])

    def test_process_has_escape(self):
        text = r"Parens[^parens](they look like \(\))"
        result = list(formatting.Footnotes().process(text))
        self.assertEqual(result, [{
            'text': text[len("Parens"):],
            'locations': [0],
            'footnote_data': {'ref': 'parens',
                              'note': "they look like ()"}}])
