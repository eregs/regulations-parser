defaults = {    # Used by setup.py
    'cfr': [
        'regparser.layer.meta.Meta',
        'regparser.layer.internal_citations.InternalCitationParser',
        'regparser.layer.table_of_contents.TableOfContentsLayer',
        'regparser.layer.terms.Terms',
        'regparser.layer.paragraph_markers.ParagraphMarkers',
        'regparser.layer.key_terms.KeyTerms',
    ],
    'preamble': [
        'regparser.layer.preamble.key_terms.KeyTerms',
        'regparser.layer.preamble.internal_citations.InternalCitations',
        'regparser.layer.preamble.paragraph_markers.ParagraphMarkers'
    ],
    'ALL': [
        'regparser.layer.external_citations.ExternalCitationParser',
        'regparser.layer.formatting.Formatting',
        'regparser.layer.graphics.Graphics',
    ],
}
