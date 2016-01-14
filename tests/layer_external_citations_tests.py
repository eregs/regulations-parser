# vim: set encoding=utf-8
from unittest import TestCase

from mock import patch

from regparser.layer.external_citations import ExternalCitationParser
from regparser.tree.struct import Node


class ParseTest(TestCase):
    def test_public_law(self):
        """
            Ensure that we successfully parse Public Law citations that look
            like the following: Public Law 111-203
        """
        node = Node("Public Law 111-203", label=['1005', '2'])
        citations = ExternalCitationParser(None).process(node)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]['text'], node.text)
        self.assertEqual(citations[0]['citation_type'], 'PUBLIC_LAW')
        self.assertEqual(citations[0]['components'],
                         {'congress': '111', 'lawnum': '203'})
        self.assertEqual(citations[0]['locations'], [0])
        self.assertTrue('url' in citations[0])

    def test_statues_at_large(self):
        """
            Ensure that we successfully parse Statues at Large citations that
            look like the following: 122 Stat. 1375
        """
        node = Node('122 Stat. 1375', label=['1003', '5'])
        citations = ExternalCitationParser(None).process(node)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]['text'], node.text)
        self.assertEqual(citations[0]['citation_type'], 'STATUTES_AT_LARGE')
        self.assertEqual(citations[0]['components'],
                         {'volume': '122', 'page': '1375'})
        self.assertEqual(citations[0]['locations'], [0])
        self.assertTrue('url' in citations[0])

    def test_cfr(self):
        """Ensure that we successfully parse CFR references."""
        node = Node("Ref 1: 12 CFR part 1026. Ref 2: 12 CFR 1026.13.",
                    label=['1003'])
        citations = ExternalCitationParser(None).process(node)
        first, second = citations

        self.assertEqual(first['text'], '12 CFR part 1026')
        self.assertEqual(first['citation_type'], 'CFR')
        self.assertEqual(first['components'],
                         {'cfr_title': '12', 'part': '1026'})
        self.assertEqual(first['locations'], [0])
        self.assertTrue('url' in first)

        self.assertEqual(second['text'], '12 CFR 1026.13')
        self.assertEqual(second['citation_type'], 'CFR')
        self.assertEqual(second['components'],
                         {'cfr_title': '12', 'part': '1026', 'section': '13'})
        self.assertEqual(second['locations'], [0])
        self.assertTrue('url' in second)

    def test_drop_self_referential_cfr(self):
        """
            Ensure that CFR references that refer to the reg being parsed are
            not marked as external citations.
        """
        node = Node("11 CFR 110.14", label=['110', '1'])
        citations = ExternalCitationParser(None).process(node)
        self.assertEqual(None, citations)

    def test_custom(self):
        """Ensure that custom citations are found. Also verify multiple
        matches are found and word boundaries respected"""
        node = Node("This has MAGIC text. Not magic, or MAGICAL, but MAGIC")
        to_patch = ('regparser.layer.external_types.settings.'
                    'CUSTOM_CITATIONS')

        with patch.dict(to_patch, {'MAGIC': 'http://example.com/magic'}):
            citations = ExternalCitationParser(None).process(node)

        self.assertEqual(1, len(citations))
        self.assertEqual(citations[0], {'text': 'MAGIC',
                                        'citation_type': 'OTHER',
                                        'components': {},
                                        'url': 'http://example.com/magic',
                                        'locations': [0, 2]})
