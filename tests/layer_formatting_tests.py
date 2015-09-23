from unittest import TestCase

from regparser.layer import formatting
from regparser.tree.struct import Node
from tests.xml_builder import XMLBuilderMixin


class LayerFormattingTests(XMLBuilderMixin, TestCase):
    def test_build_header(self):
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


    def test_awkward_table(self):
        """

        |R1C1     |R1C2               |
        |R2C1|R2C2|R2C3     |R2C4     |
        |    |    |R3C1|R3C2|R3C3|R3C4|

        """
        with self.tree.builder("GPOTABLE", COLS="2") as root:
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
        # There are three rows in the header:
        self.assertEqual(len(data["header"]), 3)
        # Verify length of each row:
        self.assertEqual(len(data["header"][0]), 2)
        self.assertEqual(len(data["header"][1]), 4)
        self.assertEqual(len(data["header"][2]), 4)

        # Check rowspans and colspans:
        cell = data["header"][0][0]
        self.assertEqual(cell["text"], 'R1C1')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 2)
        cell = data["header"][0][1]
        self.assertEqual(cell["text"], 'R1C2')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 4)
        cell = data["header"][1][0]
        self.assertEqual(cell["text"], 'R2C1')
        self.assertEqual(cell["rowspan"], 2)
        self.assertEqual(cell["colspan"], 1)
        cell = data["header"][1][1]
        self.assertEqual(cell["text"], 'R2C2')
        self.assertEqual(cell["rowspan"], 2)
        self.assertEqual(cell["colspan"], 1)
        cell = data["header"][1][2]
        self.assertEqual(cell["text"], 'R2C3')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 2)
        cell = data["header"][1][3]
        self.assertEqual(cell["text"], 'R2C4')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 2)
        cell = data["header"][2][0]
        self.assertEqual(cell["text"], 'R3C1')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 1)
        cell = data["header"][2][1]
        self.assertEqual(cell["text"], 'R3C2')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 1)
        cell = data["header"][2][2]
        self.assertEqual(cell["text"], 'R3C3')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 1)
        cell = data["header"][2][3]
        self.assertEqual(cell["text"], 'R3C4')
        self.assertEqual(cell["rowspan"], 1)
        self.assertEqual(cell["colspan"], 1)

    def test_process_fenced(self):
        node = Node("Content content\n```abc def\nLine 1\nLine 2\n```")
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]
        self.assertEqual(result['text'], node.text[16:])
        self.assertEqual(result['fence_data'],
                         {'type': 'abc def', 'lines': ['Line 1', 'Line 2']})

    def test_process_subscript(self):
        node = Node("This is a_{subscript}. And then a_{subscript} again")
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]
        self.assertEqual(result['text'], "a_{subscript}")
        self.assertEqual(result['locations'], [0, 1])
        self.assertEqual(result['subscript_data'],
                         {'variable': 'a', 'subscript': 'subscript'})

    def test_process_dashes(self):
        node = Node("This is an fp-dash_____")
        result = formatting.Formatting(None).process(node)
        self.assertEqual(1, len(result))
        result = result[0]

        self.assertEqual(result['text'], "This is an fp-dash_____")
        self.assertEqual(result['locations'], [0])
        self.assertEqual(result['dash_data'],
                         {'text': 'This is an fp-dash'})
