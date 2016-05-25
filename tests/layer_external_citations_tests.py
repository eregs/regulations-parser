# vim: set encoding=utf-8
from unittest import TestCase

from mock import patch

from regparser.layer.external_citations import ExternalCitationParser
from regparser.tree.struct import Node


def get_citation(citations, text):
    """
        Return the 1st citation whose text matches the given text
    """
    matched = [c for c in citations if c['text'] == text]
    if matched:
        return matched[0]
    return None


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

        cit_1026 = get_citation(citations, '12 CFR part 1026')
        self.assertEqual(cit_1026['citation_type'], 'CFR')
        self.assertEqual(cit_1026['components'],
                         {'cfr_title': '12', 'part': '1026'})
        self.assertEqual(cit_1026['locations'], [0])
        self.assertTrue('url' in cit_1026)

        cit_1026_13 = get_citation(citations, '12 CFR 1026.13')
        self.assertEqual(cit_1026_13['citation_type'], 'CFR')
        self.assertEqual(cit_1026_13['components'],
                         {'cfr_title': '12', 'part': '1026', 'section': '13'})
        self.assertEqual(cit_1026_13['locations'], [0])
        self.assertTrue('url' in cit_1026_13)

    def test_cfr_multiple(self):
        """Ensure that we successfully parse multiple CFR references."""
        node = Node("Some text 26 CFR 601.121 through 601.125 some more text",
                    label=['1003'])
        citations = ExternalCitationParser(None).process(node)

        cit_601_121 = get_citation(citations, '26 CFR 601.121')
        self.assertEqual(cit_601_121['citation_type'], 'CFR')
        self.assertEqual(cit_601_121['components'],
                         {'cfr_title': '26', 'part': '601', 'section': '121'})
        self.assertEqual(cit_601_121['locations'], [0])
        self.assertTrue('url' in cit_601_121)

        cit_601_125 = get_citation(citations, '601.125')
        self.assertEqual(cit_601_125['citation_type'], 'CFR')
        self.assertEqual(cit_601_125['components'],
                         {'cfr_title': '26', 'part': '601', 'section': '125'})
        self.assertEqual(cit_601_125['locations'], [0])
        self.assertTrue('url' in cit_601_125)

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
