# vim: set encoding=utf-8
from unittest import TestCase

from lxml import etree

from regparser.notice import build, changes
from regparser.notice.diff import DesignateAmendment, Amendment
from regparser.tree.struct import Node
from tests.xml_builder import XMLBuilderMixin


class NoticeBuildTest(XMLBuilderMixin, TestCase):
    def test_build_notice(self):
        fr = {
            'abstract': 'sum sum sum',
            'action': 'actact',
            'agency_names': ['Agency 1', 'Agency 2'],
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
        for key in ['agency_names', 'cfr_parts']:
            actual_notice[key] = sorted(actual_notice[key])
        self.assertEqual(actual_notice, {
            'abstract': 'sum sum sum',
            'action': 'actact',
            'agency_names': ['Agency 1', 'Agency 2'],
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
        with self.tree.builder("ROOT") as root:
            with root.SUPLINF() as suplinf:
                with suplinf.FURINF() as furinf:
                    furinf.HD("CONTACT INFO:")
                    furinf.P("Extra contact info here")
                with suplinf.ADD() as add:
                    add.P("Email: example@example.com")
                    add.P("Extra instructions")
                suplinf.HD("Supplementary Info", SOURCE="HED")
                suplinf.HD("V. Section-by-Section Analysis", SOURCE="HD1")
                suplinf.HD("8(q) Words", SOURCE="HD2")
                suplinf.P("Content")
                suplinf.HD("Section that follows", SOURCE="HD1")
                suplinf.P("Following Content")
        notice = {'cfr_parts': ['9292'], 'meta': {'start_page': 100}}
        self.assertEqual(build.process_xml(notice, self.tree.render_xml()), {
            'cfr_parts': ['9292'],
            'footnotes': {},
            'meta': {'start_page': 100},
            'addresses': {
                'methods': [('Email', 'example@example.com')],
                'instructions': ['Extra instructions']
            },
            'contact': 'Extra contact info here',
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
        with self.tree.builder("ROOT") as root:
            with root.SUPLINF() as suplinf:
                suplinf.HD("Supplementary Info", SOURCE="HED")
                suplinf.HD("V. Section-by-Section Analysis", SOURCE="HD1")
                suplinf.HD("8(q) Words", SOURCE="HD2")
                suplinf.P("Content")
                suplinf.HD("Section that follows", SOURCE="HD1")
                suplinf.P("Following Content")
        notice = {'cfr_parts': ['9292'], 'meta': {'start_page': 210}}
        self.assertEqual(build.process_xml(notice, self.tree.render_xml()), {
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
        with self.tree.builder("ROOT") as root:
            with root.DATES() as dates:
                dates.P("Effective January 1, 2002")
        xml = self.tree.render_xml()

        notice = {'cfr_parts': ['902'], 'meta': {'start_page': 10},
                  'effective_on': '2002-02-02'}
        notice = build.process_xml(notice, xml)
        self.assertEqual('2002-02-02', notice['effective_on'])

        notice = {'cfr_parts': ['902'], 'meta': {'start_page': 10}}
        notice = build.process_xml(notice, xml)
        # Uses the date found in the XML
        self.assertEqual('2002-01-01', notice['effective_on'])

        notice = {'cfr_parts': ['902'], 'meta': {'start_page': 10},
                  'effective_on': None}
        notice = build.process_xml(notice, xml)
        # Uses the date found in the XML
        self.assertEqual('2002-01-01', notice['effective_on'])

    def test_add_footnotes(self):
        with self.tree.builder("ROOT") as root:
            root.P("Some text")
            with root.FTNT() as ftnt:
                ftnt.P(_xml='<SU>21</SU>Footnote text')
            with root.FTNT() as ftnt:
                ftnt.P(_xml='<SU>43</SU>This has a<PRTPAGE P="2222" />break')
            with root.FTNT() as ftnt:
                ftnt.P(_xml='<SU>98</SU>This one has<E T="03">emph</E>tags')
        notice = {}
        build.add_footnotes(notice, self.tree.render_xml())
        self.assertEqual(notice, {'footnotes': {
            '21': 'Footnote text',
            '43': 'This has a break',
            '98': 'This one has <em data-original="E-03">emph</em> tags'
        }})

    def test_process_designate_subpart(self):
        p_list = ['200-?-1-a', '200-?-1-b']
        destination = '205-Subpart:A'
        amended_label = DesignateAmendment('DESIGNATE', p_list, destination)

        subpart_changes = build.process_designate_subpart(amended_label)

        self.assertItemsEqual(['200-1-a', '200-1-b'], subpart_changes.keys())

        for p, change in subpart_changes.items():
            self.assertEqual(change['destination'], ['205', 'Subpart', 'A'])
            self.assertEqual(change['action'], 'DESIGNATE')

    def test_process_amendments(self):
        with self.tree.builder("REGTEXT", PART="105", TITLE="12") as regtext:
            with regtext.SUBPART() as subpart:
                subpart.HD(u"Subpart A—General", SOURCE="HED")
            regtext.AMDPAR(u"2. Designate §§ 105.1 through 105.3 as subpart "
                           "A under the heading.")

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.tree.render_xml())

        section_list = ['105-2', '105-3', '105-1']
        self.assertItemsEqual(notice['changes'].keys(), section_list)

        for l, c in notice['changes'].items():
            change = c[0]
            self.assertEqual(change['destination'], ['105', 'Subpart', 'A'])
            self.assertEqual(change['action'], 'DESIGNATE')

    def test_process_amendments_section(self):
        with self.tree.builder("REGTEXT", PART="105", TITLE="12") as regtext:
            regtext.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read as "
                           "follows:")
            with regtext.SECTION() as section:
                section.SECTNO(u"§ 105.1")
                section.SUBJECT("Purpose.")
                section.STARS()
                section.P("(b) This part carries out.")

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertItemsEqual(notice['changes'].keys(), ['105-1-b'])

        changes = notice['changes']['105-1-b'][0]
        self.assertEqual(changes['action'], 'PUT')
        self.assertTrue(changes['node']['text'].startswith(
            u'(b) This part carries out.'))

    def test_process_amendments_multiple_in_same_parent(self):
        with self.tree.builder("REGTEXT", PART="105", TITLE="12") as regtext:
            regtext.AMDPAR(u"1. In § 105.1, revise paragraph (b) to read as "
                           "follows:")
            regtext.AMDPAR("2. Also, revise paragraph (c):")
            with regtext.SECTION() as section:
                section.SECTNO(u"§ 105.1")
                section.SUBJECT("Purpose.")
                section.STARS()
                section.P("(b) This part carries out.")
                section.P("(c) More stuff")

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertItemsEqual(notice['changes'].keys(), ['105-1-b', '105-1-c'])

        changes = notice['changes']['105-1-b'][0]
        self.assertEqual(changes['action'], 'PUT')
        self.assertEqual(changes['node']['text'].strip(),
                         u'(b) This part carries out.')
        changes = notice['changes']['105-1-c'][0]
        self.assertEqual(changes['action'], 'PUT')
        self.assertTrue(changes['node']['text'].strip(),
                        u'(c) More stuff')

    def test_process_amendments_restart_new_section(self):
        with self.tree.builder("ROOT") as root:
            with root.REGTEXT(PART="104", TITLE="12") as regtext:
                regtext.AMDPAR("1. In Supplement I to Part 104, comment "
                               "22(a) is added")
                regtext.P("Content")
            with root.REGTEXT(PART="105", TITLE="12") as regtext:
                regtext.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read "
                               "as follows:")
                with regtext.SECTION() as section:
                    section.SECTNO(u"§ 105.1")
                    section.SUBJECT("Purpose.")
                    section.STARS()
                    section.P("(b) This part carries out.")

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual(2, len(notice['amendments']))
        c22a, b = notice['amendments']
        self.assertEqual(c22a.action, 'POST')
        self.assertEqual(b.action, 'PUT')
        self.assertEqual(c22a.label, ['104', '22', 'a', 'Interp'])
        self.assertEqual(b.label, ['105', '1', 'b'])

    def test_process_amendments_no_nodes(self):
        with self.tree.builder("ROOT") as root:
            with root.REGTEXT(PART="104", TITLE="12") as regtext:
                regtext.AMDPAR(u"1. In § 104.13, paragraph (b) is removed")

        notice = {'cfr_parts': ['104']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual(1, len(notice['amendments']))
        delete = notice['amendments'][0]
        self.assertEqual(delete.action, 'DELETE')
        self.assertEqual(delete.label, ['104', '13', 'b'])

    def test_process_amendments_markerless(self):
        with self.tree.builder("REGTEXT", PART="105", TITLE="12") as regtext:
            regtext.AMDPAR(u"1. Revise [label:105-11-p5] as blah")
            with regtext.SECTION() as section:
                section.SECTNO(u"§ 105.11")
                section.SUBJECT("Purpose.")
                section.STARS()
                section.P("Some text here")

        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.tree.render_xml())
        self.assertItemsEqual(notice['changes'].keys(), ['105-11-p5'])

        changes = notice['changes']['105-11-p5'][0]
        self.assertEqual(changes['action'], 'PUT')

    def test_process_amendments_multiple_sections(self):
        """Regression test verifying multiple SECTIONs in the same REGTEXT"""
        with self.tree.builder("REGTEXT", PART="111") as regtext:
            regtext.AMDPAR(u"1. Modify § 111.22 by revising paragraph (b)")
            with regtext.SECTION() as section:
                section.SECTNO(u"§ 111.22")
                section.SUBJECT("Subject Here.")
                section.STARS()
                section.P("(b) Revised second paragraph")
            regtext.AMDPAR(u"2. Modify § 111.33 by revising paragraph (c)")
            with regtext.SECTION() as section:
                section.SECTNO(u"§ 111.33")
                section.SUBJECT("Another Subject")
                section.STARS()
                section.P("(c) Revised third paragraph")

        notice = {'cfr_parts': ['111']}
        build.process_amendments(notice, self.tree.render_xml())
        self.assertItemsEqual(notice['changes'].keys(),
                              ['111-22-b', '111-33-c'])

    def new_subpart_xml(self):
        with self.tree.builder("RULE") as rule:
            with rule.REGTEXT(PART="105", TITLE="12") as regtext:
                regtext.AMDPAR(u"3. In § 105.1, revise paragraph (b) to read "
                               "as follows:")
                with regtext.SECTION() as section:
                    section.SECTNO(u"§ 105.1")
                    section.SUBJECT("Purpose.")
                    section.STARS()
                    section.P("(b) This part carries out.")
            with rule.REGTEXT(PART="105", TITLE="12") as regtext:
                regtext.AMDPAR("6. Add subpart B to read as follows:")
                with regtext.CONTENTS() as contents:
                    with contents.SUBPART() as subpart:
                        subpart.SECHD("Sec.")
                        subpart.SECTNO("105.30")
                        subpart.SUBJECT("First In New Subpart.")
                with regtext.SUBPART() as subpart:
                    subpart.HD(u"Subpart B—Requirements", SOURCE="HED")
                    with subpart.SECTION() as section:
                        section.SECTNO("105.30")
                        section.SUBJECT("First In New Subpart")
                        section.P("For purposes of this subpart, the follow "
                                  "apply:")
                        section.P('(a) "Agent" means agent.')
        return self.tree.render_xml()

    def test_process_new_subpart(self):
        par = self.new_subpart_xml().xpath('//AMDPAR')[1]

        amended_label = Amendment('POST', '105-Subpart:B')
        notice = {'cfr_parts': ['105']}
        subpart_changes = build.process_new_subpart(notice, amended_label, par)

        new_nodes_added = ['105-Subpart-B', '105-30', '105-30-a']
        self.assertItemsEqual(new_nodes_added, subpart_changes.keys())

        for l, n in subpart_changes.items():
            self.assertEqual(n['action'], 'POST')

        self.assertEqual(
            subpart_changes['105-Subpart-B']['node']['node_type'], 'subpart')

    def test_process_amendments_subpart(self):
        notice = {'cfr_parts': ['105']}
        build.process_amendments(notice, self.new_subpart_xml())

        self.assertTrue('105-Subpart-B' in notice['changes'].keys())
        self.assertTrue('105-30-a' in notice['changes'].keys())
        self.assertTrue('105-30' in notice['changes'].keys())

    def test_process_amendments_mix_regs(self):
        """Some notices apply to multiple regs. For now, just ignore the
        sections not associated with the reg we're focused on"""
        with self.tree.builder("ROOT") as root:
            with root.REGTEXT(PART="105", TITLE="12") as regtext:
                regtext.AMDPAR(u"3. In § 105.1, revise paragraph (a) to read "
                               "as follows:")
                with regtext.SECTION() as section:
                    section.SECTNO(u"§ 105.1")
                    section.SUBJECT("105Purpose.")
                    section.P("(a) 105Content")
            with root.REGTEXT(PART="106", TITLE="12") as regtext:
                regtext.AMDPAR(u"3. In § 106.3, revise paragraph (b) to read "
                               "as follows:")
                with regtext.SECTION() as section:
                    section.SECTNO(u"§ 106.3")
                    section.SUBJECT("106Purpose.")
                    section.P("(b) Content")

        notice = {'cfr_parts': ['105', '106']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual(2, len(notice['changes']))
        self.assertTrue('105-1-a' in notice['changes'])
        self.assertTrue('106-3-b' in notice['changes'])

    def test_process_amendments_context(self):
        """Context should carry over between REGTEXTs"""
        with self.tree.builder("ROOT") as root:
            with root.REGTEXT(TITLE="12") as regtext:
                regtext.AMDPAR(u"3. In § 106.1, revise paragraph (a) to "
                               "read as follows:")
            with root.REGTEXT(TITLE="12") as regtext:
                regtext.AMDPAR("3. Add appendix C")

        notice = {'cfr_parts': ['105', '106']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual(2, len(notice['amendments']))
        amd1, amd2 = notice['amendments']
        self.assertEqual(['106', '1', 'a'], amd1.label)
        self.assertEqual(['106', 'C'], amd2.label)

    def test_process_amendments_insert_in_order(self):
        with self.tree.builder("ROOT") as root:
            with root.REGTEXT(TITLE="10") as regtext:
                regtext.AMDPAR('[insert-in-order] [label:123-45-p6]')
                with regtext.SECTION() as section:
                    section.SECTNO(u"§ 123.45")
                    section.SUBJECT("Some Subject.")
                    section.STARS()
                    section.P("This is the sixth paragraph")
                    section.STARS()
        notice = {'cfr_parts': ['123']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual(1, len(notice['amendments']))
        amendment = notice['amendments'][0]
        self.assertEqual(['123', '45', 'p6'], amendment.label)
        self.assertEqual('INSERT', amendment.action)

    def test_introductory_text(self):
        """ Sometimes notices change just the introductory text of a paragraph
        (instead of changing the entire paragraph tree).  """
        with self.tree.builder("REGTEXT", PART="106", TITLE="12") as regtext:
            regtext.AMDPAR(u"3. In § 106.2, revise the introductory text to "
                           "read as follows:")
            with regtext.SECTION() as section:
                section.SECTNO(u"§ 106.2")
                section.SUBJECT(" Definitions ")
                section.P(" Except as otherwise provided, the following "
                          "apply. ")
        notice = {'cfr_parts': ['106']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual('[text]', notice['changes']['106-2'][0]['field'])

    def test_multiple_changes(self):
        """ A notice can have two modifications to a paragraph. """
        with self.tree.builder("ROOT") as root:
            with root.REGTEXT(PART="106", TITLE="12") as regtext:
                regtext.AMDPAR(u"2. Designate §§ 106.1 through 106.3 as "
                               "subpart A under the heading.")
            with root.REGTEXT(PART="106", TITLE="12") as regtext:
                regtext.AMDPAR(u"3. In § 106.2, revise the introductory text "
                               "to read as follows:")
                with regtext.SECTION() as section:
                    section.SECTNO(u"§ 106.2")
                    section.SUBJECT(" Definitions ")
                    section.P(" Except as otherwise provided, the following "
                              "apply. ")
        notice = {'cfr_parts': ['106']}
        build.process_amendments(notice, self.tree.render_xml())

        self.assertEqual(2, len(notice['changes']['106-2']))

    def test_create_xmlless_changes(self):
        labels_amended = [Amendment('DELETE', '200-2-a'),
                          Amendment('MOVE', '200-2-b', '200-2-c')]
        notice_changes = changes.NoticeChanges()
        build.create_xmlless_changes(labels_amended, notice_changes)

        delete = notice_changes.changes['200-2-a'][0]
        move = notice_changes.changes['200-2-b'][0]
        self.assertEqual({'action': 'DELETE'}, delete)
        self.assertEqual({'action': 'MOVE', 'destination': ['200', '2', 'c']},
                         move)

    def test_create_xml_changes_reserve(self):
        labels_amended = [Amendment('RESERVE', '200-2-a')]

        n2a = Node('[Reserved]', label=['200', '2', 'a'])
        n2 = Node('n2', label=['200', '2'], children=[n2a])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)

        reserve = notice_changes.changes['200-2-a'][0]
        self.assertEqual(reserve['action'], 'RESERVE')
        self.assertEqual(reserve['node']['text'], u'[Reserved]')

    def test_create_xml_changes_stars(self):
        labels_amended = [Amendment('PUT', '200-2-a')]
        n2a1 = Node('(1) Content', label=['200', '2', 'a', '1'])
        n2a2 = Node('(2) Content', label=['200', '2', 'a', '2'])
        n2a = Node('(a) * * *', label=['200', '2', 'a'], children=[n2a1, n2a2])
        n2 = Node('n2', label=['200', '2'], children=[n2a])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)

        for label in ('200-2-a-1', '200-2-a-2'):
            self.assertTrue(label in notice_changes.changes)
            self.assertEqual(1, len(notice_changes.changes[label]))
            change = notice_changes.changes[label][0]
            self.assertEqual('PUT', change['action'])
            self.assertFalse('field' in change)

        self.assertTrue('200-2-a' in notice_changes.changes)
        self.assertEqual(1, len(notice_changes.changes['200-2-a']))
        change = notice_changes.changes['200-2-a'][0]
        self.assertEqual('KEEP', change['action'])
        self.assertFalse('field' in change)

    def test_create_xml_changes_stars_hole(self):
        labels_amended = [Amendment('PUT', '200-2-a')]
        n2a1 = Node('(1) * * *', label=['200', '2', 'a', '1'])
        n2a2 = Node('(2) a2a2a2', label=['200', '2', 'a', '2'])
        n2a = Node('(a) aaa', label=['200', '2', 'a'], children=[n2a1, n2a2])
        n2 = Node('n2', label=['200', '2'], children=[n2a])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)

        for label in ('200-2-a', '200-2-a-2'):
            self.assertTrue(label in notice_changes.changes)
            self.assertEqual(1, len(notice_changes.changes[label]))
            change = notice_changes.changes[label][0]
            self.assertEqual('PUT', change['action'])
            self.assertFalse('field' in change)

        self.assertTrue('200-2-a-1' in notice_changes.changes)
        self.assertEqual(1, len(notice_changes.changes['200-2-a-1']))
        change = notice_changes.changes['200-2-a-1'][0]
        self.assertEqual('KEEP', change['action'])
        self.assertFalse('field' in change)

    def test_create_xml_changes_child_stars(self):
        labels_amended = [Amendment('PUT', '200-2-a')]
        xml = etree.fromstring("<ROOT><P>(a) Content</P><STARS /></ROOT>")
        n2a = Node('(a) Content', label=['200', '2', 'a'],
                   source_xml=xml.xpath('//P')[0])
        n2b = Node('(b) Content', label=['200', '2', 'b'])
        n2 = Node('n2', label=['200', '2'], children=[n2a, n2b])
        root = Node('root', label=['200'], children=[n2])

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)

        self.assertTrue('200-2-a' in notice_changes.changes)
        self.assertTrue(1, len(notice_changes.changes['200-2-a']))
        change = notice_changes.changes['200-2-a'][0]
        self.assertEqual('PUT', change['action'])
        self.assertFalse('field' in change)

        n2a.text = n2a.text + ":"
        n2a.source_xml.text = n2a.source_xml.text + ":"

        notice_changes = changes.NoticeChanges()
        build.create_xml_changes(labels_amended, root, notice_changes)

        self.assertTrue('200-2-a' in notice_changes.changes)
        self.assertTrue(1, len(notice_changes.changes['200-2-a']))
        change = notice_changes.changes['200-2-a'][0]
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
        with self.tree.builder("RULE") as rule:
            with rule.PREAMB() as preamb:
                preamb.CFR("12 CFR Parts 1002, 1024, and 1026")
        result = build.fetch_cfr_parts(self.tree.render_xml())
        self.assertEqual(result, ['1002', '1024', '1026'])
