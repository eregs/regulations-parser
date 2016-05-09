# vim: set encoding=utf-8
from unittest import TestCase

from regparser.notice import build
from regparser.test_utils.xml_builder import XMLBuilder


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
        """Integration test for xml processing, including validating that some
        fields may be missing"""
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
