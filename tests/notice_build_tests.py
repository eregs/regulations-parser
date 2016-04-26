# vim: set encoding=utf-8
from unittest import TestCase

from lxml import etree

from regparser.notice import build, changes
from regparser.notice.amdparser import Amendment
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.xml_parser.preprocessors import ParseAMDPARs
from regparser.tree.struct import Node


class NoticeBuildTest(TestCase):
    def test_build_notice(self):
        fr = {
            'cfr_references': [{'title': 12, 'part': 9191},
                               {'title': 12, 'part': 9292}],
            'citation': 'citation citation',
            'comments_close_on': None,
            'dates': 'date info',
            'document_number': '7878-111',
            'effective_on': '1956-09-09',
            'end_page': 9999,
            'full_text_xml_url': None,
            'html_url': 'some url',
            'publication_date': '1955-12-10',
            'regulation_id_numbers': ['a231a-232q'],
            'start_page': 8888,
            'type': 'Rule',
            'volume': 66,
        }
        notices = build.build_notice('5', '9292', fr)
        self.assertEqual(1, len(notices))
        actual_notice = notices[0]
        actual_notice['cfr_parts'] = sorted(actual_notice['cfr_parts'])
        self.assertEqual(actual_notice, {
            'cfr_parts': ['9191', '9292'],
            'cfr_title': '5',
            'document_number': '7878-111',
            'effective_on': '1956-09-09',
            'fr_citation': 'citation citation',
            'fr_url': 'some url',
            'fr_volume': 66,
            'initial_effective_on': '1956-09-09',
            'meta': {
                'dates': 'date info',
                'end_page': 9999,
                'start_page': 8888,
                'type': 'Rule'
            },
            'publication_date': '1955-12-10',
            'regulation_id_numbers': ['a231a-232q'],
        })

    def test_process_xml(self):
        """Integration test for xml processing"""
        with XMLBuilder("ROOT") as ctx:
            with ctx.SUPLINF():
                ctx.HD("Supplementary Info", SOURCE="HED")
                ctx.HD("V. Section-by-Section Analysis", SOURCE="HD1")
                ctx.HD("8(q) Words", SOURCE="HD2")
                ctx.P("Content")
                ctx.HD("Section that follows", SOURCE="HD1")
                ctx.P("Following Content")
        notice = {'cfr_parts': ['9292'], 'meta': {'start_page': 100}}
        self.assertEqual(build.process_xml(notice, ctx.xml), {
            'cfr_parts': ['9292'],
            'footnotes': {},
            'meta': {'start_page': 100},
            'section_by_section': [{
                'title': '8(q) Words',
                'paragraphs': ['Content'],
                'children': [],
                'footnote_refs': [],
                'page': 100,
                'labels': ['9292-8-q']
            }],
        })

    def test_process_xml_missing_fields(self):
        with XMLBuilder("ROOT") as ctx:
            with ctx.SUPLINF():
                ctx.HD("Supplementary Info", SOURCE="HED")
                ctx.HD("V. Section-by-Section Analysis", SOURCE="HD1")
                ctx.HD("8(q) Words", SOURCE="HD2")
                ctx.P("Content")
                ctx.HD("Section that follows", SOURCE="HD1")
                ctx.P("Following Content")
        notice = {'cfr_parts': ['9292'], 'meta': {'start_page': 210}}
        self.assertEqual(build.process_xml(notice, ctx.xml), {
            'cfr_parts': ['9292'],
            'footnotes': {},
            'meta': {'start_page': 210},
            'section_by_section': [{
                'title': '8(q) Words',
                'paragraphs': ['Content'],
                'children': [],
                'footnote_refs': [],
                'page': 210,
                'labels': ['9292-8-q']
            }],
        })

    def test_process_xml_fill_effective_date(self):
        with XMLBuilder("ROOT") as ctx:
            with ctx.DATES():
                ctx.P("Effective January 1, 2002")

        notice = {'cfr_parts': ['902'], 'meta': {'start_page': 10},
                  'effective_on': '2002-02-02'}
        notice = build.process_xml(notice, ctx.xml)
        self.assertEqual('2002-02-02', notice['effective_on'])

        notice = {'cfr_parts': ['902'], 'meta': {'start_page': 10}}
        notice = build.process_xml(notice, ctx.xml)
        # Uses the date found in the XML
        self.assertEqual('2002-01-01', notice['effective_on'])

        notice = {'cfr_parts': ['902'], 'meta': {'start_page': 10},
                  'effective_on': None}
        notice = build.process_xml(notice, ctx.xml)
        # Uses the date found in the XML
        self.assertEqual('2002-01-01', notice['effective_on'])

    def test_add_footnotes(self):
        with XMLBuilder("ROOT") as ctx:
            ctx.P("Some text")
            ctx.child_from_string(
                '<FTNT><P><SU>21</SU>Footnote text</P></FTNT>')
            ctx.child_from_string(
                '<FTNT><P><SU>43</SU>This has a<PRTPAGE P="2222" />break'
                '</P></FTNT>')
            ctx.child_from_string(
                '<FTNT><P><SU>98</SU>This one has<E T="03">emph</E>tags</P>'
                '</FTNT>')
        notice = {}
        build.add_footnotes(notice, ctx.xml)
        self.assertEqual(notice, {'footnotes': {
            '21': 'Footnote text',
            '43': 'This has a break',
            '98': 'This one has <em data-original="E-03">emph</em> tags'
        }})

    def test_process_designate_subpart(self):
        amended_label = Amendment('MOVE_INTO_SUBPART', '200-?-1-a',
                                  '205-Subpart:A')

        subpart_changes = build.process_designate_subpart(amended_label)

        self.assertItemsEqual(['200-1-a'], subpart_changes.keys())
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

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, ctx.xml)
        amendment = notice['amendments'][0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '105')
        self.assertItemsEqual(['105-1', '105-2', '105-3'],
                              changes.keys())
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

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, ctx.xml)
        amendment = notice['amendments'][0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '105')
        self.assertEqual(changes.keys(), ['105-1-b'])

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

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, ctx.xml)

        amd1, amd2 = notice['amendments']
        changes1, changes2 = dict(amd1['changes']), dict(amd2['changes'])
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '105')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '105')
        self.assertEqual(changes1.keys(), ['105-1-b'])
        self.assertEqual(changes2.keys(), ['105-1-c'])

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

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, ctx.xml)

        self.assertEqual(2, len(notice['amendments']))
        amd1, amd2 = notice['amendments']
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

        notice = {'cfr_parts': ['104']}
        build.process_amendments(notice, ctx.xml)

        amendment = notice['amendments'][0]
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

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, ctx.xml)
        amendment = notice['amendments'][0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '105')
        self.assertEqual(changes.keys(), ['105-11-p5'])
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

        notice = {'cfr_parts': ['111']}
        build.process_amendments(notice, ctx.xml)
        amd1, amd2 = notice['amendments']
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '111')
        self.assertEqual(dict(amd1['changes']).keys(), ['111-22-b'])
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '111')
        self.assertEqual(dict(amd2['changes']).keys(), ['111-33-c'])

    def new_subpart_xml(self):
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
        return ctx.xml

    def test_process_amendments_subpart(self):
        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.new_subpart_xml())

        subpart_amendment = notice['amendments'][1]
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

        notice = {'cfr_parts': ['105', '106']}
        build.process_amendments(notice, ctx.xml)

        amd1, amd2 = notice['amendments']
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '105')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '106')
        self.assertEqual(['105-1-a'], dict(amd1['changes']).keys())
        self.assertEqual(['106-3-b'], dict(amd2['changes']).keys())

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

        notice = {'cfr_parts': ['105', '106']}
        build.process_amendments(notice, ctx.xml)

        amd1, amd2 = notice['amendments']
        self.assertEqual(amd1['instruction'], amdpar1)
        self.assertEqual(amd1['cfr_part'], '106')
        self.assertEqual(amd2['instruction'], amdpar2)
        self.assertEqual(amd2['cfr_part'], '106')
        self.assertEqual(['106-1-a'], dict(amd1['changes']).keys())
        self.assertItemsEqual(['106-C', '106-C-p1'],
                              dict(amd2['changes']).keys())

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
        notice = {'cfr_parts': ['123']}
        build.process_amendments(notice, ctx.xml)

        amendment = notice['amendments'][0]
        changes = dict(amendment['changes'])

        self.assertEqual(amendment['instruction'], amdpar)
        self.assertEqual(amendment['cfr_part'], '123')
        self.assertEqual(['123-45-p6'], changes.keys())
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
        notice = {'cfr_parts': ['123']}
        build.process_amendments(notice, ctx.xml)

        amendment = notice['amendments'][0]
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
        notice = {'cfr_parts': ['106']}
        build.process_amendments(notice, ctx.xml)

        change = dict(notice['amendments'][0]['changes'])['106-2'][0]
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
        notice = {'cfr_parts': ['106']}
        build.process_amendments(notice, ctx.xml)

        amd1, amd2 = notice['amendments']
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
            build.create_xmlless_change(amendment, notice_changes)

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
        build.create_xml_changes(labels_amended, root, notice_changes)

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
        build.create_xml_changes(labels_amended, root, notice_changes)
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
        build.create_xml_changes(labels_amended, root, notice_changes)

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
        xml = etree.fromstring("<ROOT><P>(a) Content</P><STARS /></ROOT>")
        n2a = Node('(a) Content', label=['200', '2', 'a'],
                   source_xml=xml.xpath('//P')[0])
        n2b = Node('(b) Content', label=['200', '2', 'b'])
        n2 = Node('n2', label=['200', '2'], children=[n2a, n2b])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)
        data = notice_changes.changes_by_xml[None]

        self.assertIn('200-2-a', data)
        self.assertTrue(1, len(data['200-2-a']))
        change = data['200-2-a'][0]
        self.assertEqual('PUT', change['action'])
        self.assertNotIn('field', change)

        n2a.text = n2a.text + ":"
        n2a.source_xml.text = n2a.source_xml.text + ":"

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)
        data = notice_changes.changes_by_xml[None]

        self.assertIn('200-2-a', data)
        self.assertTrue(1, len(data['200-2-a']))
        change = data['200-2-a'][0]
        self.assertEqual('PUT', change['action'])
        self.assertEqual('[text]', change.get('field'))

    def test_split_doc_num(self):
        doc_num = '2013-2222'
        effective_date = '2014-10-11'
        self.assertEqual(
            '2013-2222_20141011',
            build.split_doc_num(doc_num, effective_date))

    def test_set_document_numbers(self):
        notice = {'document_number': '111', 'effective_on': '2013-10-08'}
        notices = build.set_document_numbers([notice])
        self.assertEqual(notices[0]['document_number'], '111')

        second_notice = {'document_number': '222',
                         'effective_on': '2013-10-10'}

        notices = build.set_document_numbers([notice, second_notice])

        self.assertEqual(notices[0]['document_number'], '111_20131008')
        self.assertEqual(notices[1]['document_number'], '222_20131010')

    def test_fetch_cfr_parts(self):
        with XMLBuilder("RULE") as ctx:
            with ctx.PREAMB():
                ctx.CFR("12 CFR Parts 1002, 1024, and 1026")
        result = build.fetch_cfr_parts(ctx.xml)
        self.assertEqual(result, ['1002', '1024', '1026'])
