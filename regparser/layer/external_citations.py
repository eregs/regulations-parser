# using relative imports due to funkiness in regparser/layer/__init__.py
from . import external_types
from .layer import Layer


class ExternalCitationParser(Layer):
    """External Citations are references to documents outside of eRegs. See
    `external_types` for specific types of external citations"""
    shorthand = 'external-citations'

    def process(self, node):
        citations = [cite
                     for finder in external_types.ALL
                     for cite in finder().find(node)]

        layer_elements = []
        for text, locations, representative in self.convert_to_search_replace(
                citations, node.text, lambda c: c.start, lambda c: c.end):
            layer_elements.append(dict(
                text=text.strip(), locations=locations, url=representative.url,
                components=representative.components,
                citation_type=representative.cite_type))

        if layer_elements:
            return layer_elements
