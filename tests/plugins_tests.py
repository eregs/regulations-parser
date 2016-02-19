from unittest import TestCase

from regparser import plugins
from regparser.layer.meta import Meta
from regparser.layer.external_citations import ExternalCitationParser


class PluginsTests(TestCase):
    _FORWARD = ['regparser.layer.meta.Meta',
                'regparser.layer.external_citations.ExternalCitationParser']
    _BACKWARD = list(reversed(_FORWARD))

    def test_class_paths_to_classes(self):
        """A list of class paths should get converted into a list of
        classes"""
        results = plugins.class_paths_to_classes(self._FORWARD)
        self.assertEqual(results, [Meta, ExternalCitationParser])

        results = plugins.class_paths_to_classes(self._BACKWARD)
        self.assertEqual(results, [ExternalCitationParser, Meta])

    def test_classes_by_shorthand(self):
        """Convert class paths into an ordered dict"""
        results = plugins.classes_by_shorthand(self._FORWARD)
        self.assertEqual(results['meta'], Meta)
        self.assertEqual(results['external-citations'], ExternalCitationParser)
        self.assertEqual(list(results)[0], 'meta')

        results = plugins.classes_by_shorthand(self._BACKWARD)
        self.assertEqual(list(results)[0], 'external-citations')
