# -*- coding: utf-8 -*-
from unittest import TestCase

from mock import patch
import six

from regparser.notice import amendments, changes
from regparser.notice.amdparser import Amendment
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.struct import Node
from regparser.tree.xml_parser.preprocessors import ParseAMDPARs


class NoticeAmendmentsTest(TestCase):
    @patch('regparser.notice.amendments.process_appendix')
    def test_parse_appendix(self, process):
        with XMLBuilder("ROOT") as ctx:
            ctx.AMDPAR("1. Adding Appendix R and S")
            ctx.HD("Appendix R to Part 1234", SOURCE="HD1")
            with ctx.EXTRACT():
                ctx.P("R1")
                ctx.P("R2")
            ctx.HD("Appendix S to Part 1234", SOURCE="HD1")
            with ctx.EXTRACT():
                ctx.P("S1")
                ctx.P("S2")

        amendments.parse_appendix(ctx.xml, '1234', 'S')
        self.assertEqual(process.call_count, 1)
        extract = process.call_args[0][0]
        self.assertEqual(['Appendix S to Part 1234', 'S1', 'S2'],
                         [n.text for n in extract])

        amendments.parse_appendix(ctx.xml, '1234', 'R')
        self.assertEqual(process.call_count, 2)
        extract = process.call_args[0][0]
        self.assertEqual(['Appendix R to Part 1234', 'R1', 'R2'],
                         [n.text for n in extract])

    @patch('regparser.notice.amendments.interpretations')
    def test_parse_interp(self, interpretations):
        xmls = []
        with XMLBuilder("REGTEXT") as ctx:
            with ctx.EXTRACT():
                ctx.P("Something")
                ctx.STARS()
                ctx.HD("Supplement I")
                ctx.HD("A")
                ctx.T1("a")
                ctx.P("b")
        xmls.append(ctx.xml)

        with XMLBuilder("REGTEXT") as ctx:
            ctx.P("Something")
            ctx.STARS()
            with ctx.SUBSECT():
                ctx.HD("Supplement I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
        xmls.append(ctx.xml)

        with XMLBuilder("REGTEXT") as ctx:
            ctx.AMDPAR("1. In Supplement I to part 111, under...")
            ctx.P("Something")
            ctx.STARS()
            ctx.HD("SUPPLEMENT I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
        xmls.append(ctx.xml)

        with XMLBuilder("REGTEXT") as ctx:
            ctx.AMDPAR("1. In Supplement I to part 111, under...")
            ctx.P("Something")
            ctx.STARS()
            with ctx.APPENDIX():
                ctx.HD("SUPPLEMENT I")
            ctx.HD("A")
            ctx.T1("a")
            ctx.P("b")
            ctx.PRTPAGE()
        xmls.append(ctx.xml)

        for xml in xmls:
            amendments.parse_interp('111', xml)
            root, nodes = interpretations.parse_from_xml.call_args[0]
            self.assertEqual(root.label, ['111', 'Interp'])
            self.assertEqual(['HD', 'T1', 'P'], [n.tag for n in nodes])

    def test_parse_interp_subpart_confusion(self):
        with XMLBuilder("REGTEXT") as ctx:
            ctx.AMDPAR("1. In Supplement I to part 111, under Section 33, "
                       "paragraph 5 is added.")
            ctx.HD("Supplement I")
            with ctx.SUBPART():
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 111.33")
                    ctx.SUBJECT("Stubby Subby")
                    ctx.STARS()
                    ctx.P("5. Some Content")
        interp = amendments.parse_interp('111', ctx.xml)
        self.assertEqual(1, len(interp.children))
        c33 = interp.children[0]
        self.assertEqual(c33.label, ['111', '33', 'Interp'])
        self.assertEqual(1, len(c33.children))
        c335 = c33.children[0]
        self.assertEqual(c335.label, ['111', '33', 'Interp', '5'])

    def test_find_section(self):
        with XMLBuilder('REGTEXT') as ctx:
            ctx.AMDPAR("In 200.1 revise paragraph (b) as follows:")
            with ctx.SECTION():
                ctx.SECTNO("200.1")
                ctx.SUBJECT("Authority and Purpose.")
                ctx.P(" (b) This part is very important. ")
            ctx.AMDPAR("In 200.3 revise paragraph (b)(1) as follows:")
            with ctx.SECTION():
                ctx.SECTNO("200.3")
                ctx.SUBJECT("Definitions")
                ctx.P(" (b)(1) Define a term here. ")

        amdpar_xml = ctx.xml.xpath('//AMDPAR')[0]
        section = amendments.find_section(amdpar_xml)
        self.assertEqual(section.tag, 'SECTION')

        sectno_xml = section.xpath('./SECTNO')[0]
        self.assertEqual(sectno_xml.text, '200.1')

    def test_find_section_paragraphs(self):
        with XMLBuilder("REGTEXT") as ctx:
            with ctx.SECTION():
                ctx.SECTNO(" 205.4 ")
                ctx.SUBJECT("[Corrected]")
            ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                       u"follows:")
            ctx.P("(b) paragraph 1")

        amdpar = ctx.xml.xpath('//AMDPAR')[0]
        section = amendments.find_section(amdpar)
        self.assertNotEqual(None, section)
        paragraphs = [p for p in section if p.tag == 'P']
        self.assertEqual(paragraphs[0].text, '(b) paragraph 1')

    def test_find_lost_section(self):
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT():
                ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                           u"follows:")
            with ctx.REGTEXT():
                with ctx.SECTION():
                    ctx.SECTNO(" 205.4 ")
                    ctx.SUBJECT("[Corrected]")
        amdpar = ctx.xml.xpath('//AMDPAR')[0]
        section = amendments.find_lost_section(amdpar)
        self.assertNotEqual(None, section)

    def test_find_section_lost(self):
        with XMLBuilder("PART") as ctx:
            with ctx.REGTEXT():
                ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                           u"follows:")
            with ctx.REGTEXT():
                with ctx.SECTION():
                    ctx.SECTNO(" 205.4 ")
                    ctx.SUBJECT("[Corrected]")
        amdpar = ctx.xml.xpath('//AMDPAR')[0]
        section = amendments.find_section(amdpar)
        self.assertNotEqual(None, section)

    def test_process_designate_subpart(self):
        amended_label = Amendment('MOVE_INTO_SUBPART', '200-?-1-a',
                                  '205-Subpart:A')

        subpart_changes = amendments.process_designate_subpart(amended_label)

        six.assertCountEqual(self, ['200-1-a'], subpart_changes.keys())
        change = subpart_changes['200-1-a']
        self.assertEqual(change['destination'], ['205', 'Subpart', 'A'])
        self.assertEqual(change['action'], 'DESIGNATE')

    def test_process_amendments(self):
        amdpar = (u"2. Designate §§ 105.1 through 105.3 as subpart A under "
                  u"the heading.")
        with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
            with ctx.SUBPART():
                ctx.HD(u"Subpart A—General", SOURCE="HED")
            ctx.AMDPAR(amdpar)
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '105')
        six.assertCountEqual(self, ['105-1', '105-2', '105-3'], changes.keys())
        for change_list in changes.values():
            self.assertEqual(1, len(change_list))
            change = change_list[0]
            self.assertEqual(change['destination'], ['105', 'Subpart', 'A'])
            self.assertEqual(change['action'], 'DESIGNATE')

    def test_process_amendments_section(self):
        amdpar = u"3. In § 105.1, revise paragraph (b) to read as follows:"
        with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
            ctx.AMDPAR(amdpar)
            with ctx.SECTION():
                ctx.SECTNO(u"§ 105.1")
                ctx.SUBJECT("Purpose.")
                ctx.STARS()
                ctx.P("(b) This part carries out.")
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '105')
        six.assertCountEqual(self, changes.keys(), ['105-1-b'])

        changes = changes['105-1-b'][0]
        self.assertEqual(changes['action'], 'PUT')
        self.assertTrue(changes['node']['text'].startswith(
            u'(b) This part carries out.'))

    def test_process_amendments_multiple_in_same_parent(self):
        amdpar1 = u"1. In § 105.1, revise paragraph (b) to read as follows:"
        amdpar2 = "2. Also, revise paragraph (c):"
        with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
            ctx.AMDPAR(amdpar1)
            ctx.AMDPAR(amdpar2)
            with ctx.SECTION():
                ctx.SECTNO(u"§ 105.1")
                ctx.SUBJECT("Purpose.")
                ctx.STARS()
                ctx.P("(b) This part carries out.")
                ctx.P("(c) More stuff")
        ParseAMDPARs().transform(ctx.xml)

        amd1, amd2 = amendments.fetch_amendments(ctx.xml)
        changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '105')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '105')
        six.assertCountEqual(self, changes1.keys(), ['105-1-b'])
        six.assertCountEqual(self, changes2.keys(), ['105-1-c'])

        changes = changes1['105-1-b'][0]
        self.assertEqual(changes['action'], 'PUT')
        self.assertEqual(changes['node']['text'].strip(),
                         u'(b) This part carries out.')
        changes = changes2['105-1-c'][0]
        self.assertEqual(changes['action'], 'PUT')
        self.assertTrue(changes['node']['text'].strip(),
                        u'(c) More stuff')

    def test_process_amendments_restart_new_section(self):
        amdpar1 = "1. In Supplement I to Part 104, comment 22(a) is added"
        amdpar2 = u"3. In § 105.1, revise paragraph (b) to read as follows:"
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(PART="104", TITLE="12"):
                ctx.AMDPAR(amdpar1)
                ctx.HD("SUPPLEMENT I", SOURCE='HED')
                ctx.HD("22(a)", SOURCE='HD1')
                ctx.P("1. Content")
            with ctx.REGTEXT(PART="105", TITLE="12"):
                ctx.AMDPAR(amdpar2)
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 105.1")
                    ctx.SUBJECT("Purpose.")
                    ctx.STARS()
                    ctx.P("(b) This part carries out.")
        ParseAMDPARs().transform(ctx.xml)

        amd1, amd2 = amendments.fetch_amendments(ctx.xml)
        changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '104')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '105')
        self.assertIn('104-22-a-Interp', changes1)
        self.assertIn('105-1-b', changes2)

        self.assertEqual(changes1['104-22-a-Interp'][0]['action'], 'POST')
        self.assertEqual(changes2['105-1-b'][0]['action'], 'PUT')

    def test_process_amendments_no_nodes(self):
        amdpar = u"1. In § 104.13, paragraph (b) is removed"
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(PART="104", TITLE="12"):
                ctx.AMDPAR(amdpar)
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '104')
        self.assertIn('104-13-b', changes)
        self.assertEqual(changes['104-13-b'][0]['action'], 'DELETE')

    def test_process_amendments_markerless(self):
        amdpar = u"1. Revise [label:105-11-p5] as blah"
        with XMLBuilder("REGTEXT", PART="105", TITLE="12") as ctx:
            ctx.AMDPAR(amdpar)
            with ctx.SECTION():
                ctx.SECTNO(u"§ 105.11")
                ctx.SUBJECT("Purpose.")
                ctx.STARS()
                ctx.P("Some text here")
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '105')
        six.assertCountEqual(self, changes.keys(), ['105-11-p5'])
        changes = changes['105-11-p5'][0]
        self.assertEqual(changes['action'], 'PUT')

    def test_process_amendments_multiple_sections(self):
        """Regression test verifying multiple SECTIONs in the same REGTEXT"""
        amdpar1 = u"1. Modify § 111.22 by revising paragraph (b)"
        amdpar2 = u"2. Modify § 111.33 by revising paragraph (c)"
        with XMLBuilder("REGTEXT", PART="111") as ctx:
            ctx.AMDPAR(amdpar1)
            with ctx.SECTION():
                ctx.SECTNO(u"§ 111.22")
                ctx.SUBJECT("Subject Here.")
                ctx.STARS()
                ctx.P("(b) Revised second paragraph")
            ctx.AMDPAR(amdpar2)
            with ctx.SECTION():
                ctx.SECTNO(u"§ 111.33")
                ctx.SUBJECT("Another Subject")
                ctx.STARS()
                ctx.P("(c) Revised third paragraph")
        ParseAMDPARs().transform(ctx.xml)

        amd1, amd2 = amendments.fetch_amendments(ctx.xml)
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '111')
        six.assertCountEqual(self,
                             [c[0] for c in amd1['changes']], ['111-22-b'])
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '111')
        six.assertCountEqual(self,
                             [c[0] for c in amd2['changes']], ['111-33-c'])

    def test_process_amendments_subpart(self):
        with XMLBuilder("RULE") as ctx:
            with ctx.REGTEXT(PART="105", TITLE="12"):
                ctx.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as"
                           u"follows:")
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 105.1")
                    ctx.SUBJECT("Purpose.")
                    ctx.STARS()
                    ctx.P("(b) This part carries out.")
            with ctx.REGTEXT(PART="105", TITLE="12"):
                ctx.AMDPAR("6. Add subpart B to read as follows:")
                with ctx.CONTENTS():
                    with ctx.SUBPART():
                        ctx.SECHD("Sec.")
                        ctx.SECTNO("105.30")
                        ctx.SUBJECT("First In New Subpart.")
                with ctx.SUBPART():
                    ctx.HD(u"Subpart B—Requirements", SOURCE="HED")
                    with ctx.SECTION():
                        ctx.SECTNO("105.30")
                        ctx.SUBJECT("First In New Subpart")
                        ctx.P("For purposes of this subpart, the follow "
                              "apply:")
                        ctx.P('(a) "Agent" means agent.')

        ParseAMDPARs().transform(ctx.xml)

        subpart_amendment = amendments.fetch_amendments(ctx.xml)[1]
        changes = dict(subpart_amendment['changes'])

        self.assertTrue('105-Subpart-B' in changes)
        self.assertTrue('105-30-a' in changes)
        self.assertTrue('105-30' in changes)

    def test_process_amendments_mix_regs(self):
        """Some notices apply to multiple regs. For now, just ignore the
        sections not associated with the reg we're focused on"""
        amdpar1 = u"3. In § 105.1, revise paragraph (a) to read as follows:"
        amdpar2 = u"3. In § 106.3, revise paragraph (b) to read as follows:"
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(PART="105", TITLE="12"):
                ctx.AMDPAR(amdpar1)
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 105.1")
                    ctx.SUBJECT("105Purpose.")
                    ctx.P("(a) 105Content")
            with ctx.REGTEXT(PART="106", TITLE="12"):
                ctx.AMDPAR(amdpar2)
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 106.3")
                    ctx.SUBJECT("106Purpose.")
                    ctx.P("(b) Content")
        ParseAMDPARs().transform(ctx.xml)

        amd1, amd2 = amendments.fetch_amendments(ctx.xml)
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '105')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '106')
        six.assertCountEqual(self,
                             [c[0] for c in amd1['changes']], ['105-1-a'])
        six.assertCountEqual(self,
                             [c[0] for c in amd2['changes']], ['106-3-b'])

    def test_process_amendments_context(self):
        """Context should carry over between REGTEXTs"""
        amdpar1 = u"3. In § 106.1, revise paragraph (a) to read as follows:"
        amdpar2 = "3. Add appendix C"
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(TITLE="12"):
                ctx.AMDPAR(amdpar1)
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 106.1")
                    ctx.SUBJECT("Some Subject.")
                    ctx.P("(a) Something new")
            with ctx.REGTEXT(TITLE="12"):
                ctx.AMDPAR(amdpar2)
                ctx.HD("Appendix C to Part 106", SOURCE="HD1")
                with ctx.EXTRACT():
                    ctx.P("Text")
        ParseAMDPARs().transform(ctx.xml)

        amd1, amd2 = amendments.fetch_amendments(ctx.xml)
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '106')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '106')
        six.assertCountEqual(self,
                             [c[0] for c in amd1['changes']], ['106-1-a'])
        six.assertCountEqual(
            self,
            [c[0] for c in amd2['changes']], ['106-C', '106-C-p1'])

    def test_process_amendments_insert_in_order(self):
        amdpar = '[insert-in-order] [label:123-45-p6]'
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(TITLE="10"):
                ctx.AMDPAR(amdpar)
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 123.45")
                    ctx.SUBJECT("Some Subject.")
                    ctx.STARS()
                    ctx.P("This is the sixth paragraph")
                    ctx.STARS()
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '123')
        six.assertCountEqual(self, ['123-45-p6'], changes.keys())
        self.assertEqual('INSERT', changes['123-45-p6'][0]['action'])

    def test_process_amendments_authority(self):
        amdpar = ('1. The authority citation for 27 CFR Part 555 continues '
                  'to read as follows:')
        auth = '18 U.S.C. 847.'
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(TITLE="27", PART="555"):
                ctx.AMDPAR(amdpar)
                with ctx.AUTH():
                    ctx.HD("Authority:", SOURCE="HED")
                    ctx.P(auth)
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '555')
        self.assertEqual(amendment['authority'], auth)
        self.assertNotIn('changes', amendment)

    def test_introductory_text(self):
        """ Sometimes notices change just the introductory text of a paragraph
        (instead of changing the entire paragraph tree).  """
        with XMLBuilder("REGTEXT", PART="106", TITLE="12") as ctx:
            ctx.AMDPAR(u"3. In § 106.2, revise the introductory text to read:")
            with ctx.SECTION():
                ctx.SECTNO(u"§ 106.2")
                ctx.SUBJECT(" Definitions ")
                ctx.P(" Except as otherwise provided, the following apply. ")
        ParseAMDPARs().transform(ctx.xml)

        amendment = amendments.fetch_amendments(ctx.xml)[0]
        change = dict(amendment['changes'])['106-2'][0]
        self.assertEqual('[text]', change.get('field'))

    def test_multiple_changes(self):
        """ A notice can have two modifications to a paragraph. """
        amdpar1 = (u"2. Designate §§ 106.1 through 106.3 as subpart A under "
                   u"the heading.")
        amdpar2 = u"3. In § 106.2, revise the introductory text to read:"
        with XMLBuilder("ROOT") as ctx:
            with ctx.REGTEXT(PART="106", TITLE="12"):
                ctx.AMDPAR(amdpar1)
            with ctx.REGTEXT(PART="106", TITLE="12"):
                ctx.AMDPAR(amdpar2)
                with ctx.SECTION():
                    ctx.SECTNO(u"§ 106.2")
                    ctx.SUBJECT(" Definitions ")
                    ctx.P(" Except as otherwise provided, the following "
                          "apply. ")
        ParseAMDPARs().transform(ctx.xml)

        amd1, amd2 = amendments.fetch_amendments(ctx.xml)
        changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '106')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '106')
        self.assertEqual(1, len(changes1['106-2']))
        self.assertEqual(1, len(changes2['106-2']))

    def test_create_xmlless_changes(self):
        labels_amended = [Amendment('DELETE', '200-?-2-a'),
                          Amendment('MOVE', '200-?-2-b', '200-?-2-c')]
        notice_changes = changes.NoticeChanges()
        for amendment in labels_amended:
            amendments.create_xmlless_change(amendment, notice_changes)

        delete = notice_changes.changes_by_xml[None]['200-2-a'][0]
        move = notice_changes.changes_by_xml[None]['200-2-b'][0]
        self.assertEqual({'action': 'DELETE'}, delete)
        self.assertEqual({'action': 'MOVE', 'destination': ['200', '2', 'c']},
                         move)

    def test_create_xml_changes_reserve(self):
        labels_amended = [Amendment('RESERVE', '200-?-2-a')]

        n2a = Node('[Reserved]', label=['200', '2', 'a'])
        n2 = Node('n2', label=['200', '2'], children=[n2a])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        amendments.create_xml_changes(labels_amended, root, notice_changes)

        reserve = notice_changes.changes_by_xml[None]['200-2-a'][0]
        self.assertEqual(reserve['action'], 'RESERVE')
        self.assertEqual(reserve['node']['text'], u'[Reserved]')

    def test_create_xml_changes_stars(self):
        labels_amended = [Amendment('PUT', '200-?-2-a')]
        n2a1 = Node('(1) Content', label=['200', '2', 'a', '1'])
        n2a2 = Node('(2) Content', label=['200', '2', 'a', '2'])
        n2a = Node('(a) * * *', label=['200', '2', 'a'], children=[n2a1, n2a2])
        n2 = Node('n2', label=['200', '2'], children=[n2a])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        amendments.create_xml_changes(labels_amended, root, notice_changes)
        data = notice_changes.changes_by_xml[None]

        for label in ('200-2-a-1', '200-2-a-2'):
            self.assertIn(label, data)
            self.assertEqual(1, len(data[label]))
            change = data[label][0]
            self.assertEqual('PUT', change['action'])
            self.assertNotIn('field', change)

        self.assertTrue('200-2-a' in data)
        self.assertEqual(1, len(data['200-2-a']))
        change = data['200-2-a'][0]
        self.assertEqual('KEEP', change['action'])
        self.assertNotIn('field', change)

    def test_create_xml_changes_stars_hole(self):
        labels_amended = [Amendment('PUT', '200-?-2-a')]
        n2a1 = Node('(1) * * *', label=['200', '2', 'a', '1'])
        n2a2 = Node('(2) a2a2a2', label=['200', '2', 'a', '2'])
        n2a = Node('(a) aaa', label=['200', '2', 'a'], children=[n2a1, n2a2])
        n2 = Node('n2', label=['200', '2'], children=[n2a])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        amendments.create_xml_changes(labels_amended, root, notice_changes)

        data = notice_changes.changes_by_xml[None]
        for label in ('200-2-a', '200-2-a-2'):
            self.assertIn(label, data)
            self.assertEqual(1, len(data[label]))
            change = data[label][0]
            self.assertEqual('PUT', change['action'])
            self.assertNotIn('field', change)

        self.assertIn('200-2-a-1', data)
        self.assertEqual(1, len(data['200-2-a-1']))
        change = data['200-2-a-1'][0]
        self.assertEqual('KEEP', change['action'])
        self.assertFalse('field' in change)

    def test_create_xml_changes_child_stars(self):
        labels_amended = [Amendment('PUT', '200-?-2-a')]
        with XMLBuilder("ROOT") as ctx:
            ctx.P("(a) Content")
            ctx.STARS()
        n2a = Node('(a) Content', label=['200', '2', 'a'],
                   source_xml=ctx.xml.xpath('//P')[0])
        n2b = Node('(b) Content', label=['200', '2', 'b'])
        n2 = Node('n2', label=['200', '2'], children=[n2a, n2b])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        amendments.create_xml_changes(labels_amended, root, notice_changes)
        data = notice_changes.changes_by_xml[None]

        self.assertIn('200-2-a', data)
        self.assertTrue(1, len(data['200-2-a']))
        change = data['200-2-a'][0]
        self.assertEqual('PUT', change['action'])
        self.assertNotIn('field', change)

        n2a.text = n2a.text + ":"
        n2a.source_xml.text = n2a.source_xml.text + ":"

        notice_changes = changes.NoticeChanges()
        amendments.create_xml_changes(labels_amended, root, notice_changes)
        data = notice_changes.changes_by_xml[None]

        self.assertIn('200-2-a', data)
        self.assertTrue(1, len(data['200-2-a']))
        change = data['200-2-a'][0]
        self.assertEqual('PUT', change['action'])
        self.assertEqual('[text]', change.get('field'))
