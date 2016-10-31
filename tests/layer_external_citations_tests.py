# -*- coding: utf-8 -*-

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


def test_public_law():
    """
        Ensure that we successfully parse Public Law citations that look
        like the following: Public Law 111-203
    """
    node = Node("Public Law 111-203", label=['1005', '2'])
    citations = ExternalCitationParser(None).process(node)
    assert len(citations) == 1
    cit = citations[0]
    assert cit['text'] == node.text
    assert cit['citation_type'] == 'PUBLIC_LAW'
    assert cit['components'] == {'congress': '111', 'lawnum': '203'}
    assert cit['locations'] == [0]
    url = cit.get('url', '')
    assert 'congress=111' in url
    assert 'lawnum=203' in url
    assert 'collection=plaw' in url
    assert 'lawtype=public' in url


def test_statues_at_large():
    """
        Ensure that we successfully parse Statues at Large citations that
        look like the following: 122 Stat. 1375
    """
    node = Node('122 Stat. 1375', label=['1003', '5'])
    citations = ExternalCitationParser(None).process(node)
    assert len(citations) == 1
    cit = citations[0]
    assert cit['text'] == node.text
    assert cit['citation_type'] == 'STATUTES_AT_LARGE'
    assert cit['components'] == {'volume': '122', 'page': '1375'}
    assert cit['locations'] == [0]
    url = cit.get('url', '')
    assert 'volume=122' in url
    assert 'page=1375' in url
    assert 'collection=statute' in url


def test_cfr():
    """Ensure that we successfully parse CFR references."""
    node = Node("Ref 1: 12 CFR part 1026. Ref 2: 12 CFR 1026.13.",
                label=['1003'])
    citations = ExternalCitationParser(None).process(node)

    cit = get_citation(citations, '12 CFR part 1026')
    assert cit['citation_type'] == 'CFR'
    assert cit['components'] == {'cfr_title': '12', 'part': '1026'}
    assert cit['locations'] == [0]
    url = cit.get('url', '')
    assert 'titlenum=12' in url
    assert 'partnum=1026' in url
    assert 'section' not in url
    assert 'collection=cfr' in url

    cit = get_citation(citations, '12 CFR 1026.13')
    assert cit['citation_type'] == 'CFR'
    assert cit['components'] == {
        'cfr_title': '12', 'part': '1026', 'section': '13'
    }
    assert cit['locations'] == [0]
    url = cit.get('url', '')
    assert 'titlenum=12' in url
    assert 'partnum=1026' in url
    assert 'section=13' in url
    assert 'collection=cfr' in url


def test_cfr_multiple():
    """Ensure that we successfully parse multiple CFR references."""
    node = Node("Some text 26 CFR 601.121 through 601.125 some more text",
                label=['1003'])
    citations = ExternalCitationParser(None).process(node)

    cit = get_citation(citations, '26 CFR 601.121')
    assert cit['citation_type'] == 'CFR'
    assert cit['components'] == {
        'cfr_title': '26', 'part': '601', 'section': '121'
    }
    assert cit['locations'] == [0]
    url = cit.get('url', '')
    assert 'titlenum=26' in url
    assert 'partnum=601' in url
    assert 'section=121' in url
    assert 'collection=cfr' in url

    cit = get_citation(citations, '601.125')
    assert cit['citation_type'] == 'CFR'
    assert cit['components'] == {
        'cfr_title': '26', 'part': '601', 'section': '125'
    }
    assert cit['locations'] == [0]
    url = cit.get('url', '')
    assert 'titlenum=26' in url
    assert 'partnum=601' in url
    assert 'section=125' in url
    assert 'collection=cfr' in url


def test_drop_self_referential_cfr():
    """
        Ensure that CFR references that refer to the reg being parsed are
        not marked as external citations.
    """
    node = Node("11 CFR 110.14", label=['110', '1'])
    citations = ExternalCitationParser(None).process(node)
    assert citations is None


def test_custom():
    """Ensure that custom citations are found. Also verify multiple
    matches are found and word boundaries respected"""
    node = Node("This has MAGIC text. Not magic, or MAGICAL, but MAGIC")
    to_patch = ('regparser.layer.external_types.settings.'
                'CUSTOM_CITATIONS')

    with patch.dict(to_patch, {'MAGIC': 'http://example.com/magic'}):
        citations = ExternalCitationParser(None).process(node)

    assert len(citations) == 1
    assert citations[0] == {
        'text': 'MAGIC',
        'citation_type': 'OTHER',
        'components': {},
        'url': 'http://example.com/magic',
        'locations': [0, 2]
    }


def test_urls():
    """If text contains http-based urls, they should be tagged"""
    node = Node("Something http://example.com, not: a url://here "
                "but https://here.is.something/with?slashes=true.")
    citations = ExternalCitationParser(None).process(node)
    urls = ['http://example.com',
            'https://here.is.something/with?slashes=true']

    assert len(citations) == 2
    for url in urls:
        citation = get_citation(citations, url)
        assert citation['url'] == url
        assert citation['text'] == url
