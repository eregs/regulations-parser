from collections import OrderedDict

from . import (
    external_citations, formatting, graphics, internal_citations,
    interpretations, key_terms, meta, paragraph_markers, section_by_section,
    table_of_contents, terms)


ALL_LAYERS = OrderedDict([
    ('external-citations', external_citations.ExternalCitationParser),
    ('meta', meta.Meta),
    ('analyses', section_by_section.SectionBySection),
    ('internal-citations', internal_citations.InternalCitationParser),
    ('toc', table_of_contents.TableOfContentsLayer),
    ('interpretations', interpretations.Interpretations),
    ('terms', terms.Terms),
    ('paragraph-markers', paragraph_markers.ParagraphMarkers),
    ('keyterms', key_terms.KeyTerms),
    ('formatting', formatting.Formatting),
    ('graphics', graphics.Graphics)
])
