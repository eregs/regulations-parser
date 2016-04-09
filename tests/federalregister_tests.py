import re
from unittest import TestCase

from mock import patch

from regparser import federalregister
from regparser.test_utils.http_mixin import HttpMixin


class FederalRegisterTest(HttpMixin, TestCase):
    @patch('regparser.federalregister.build_notice')
    def test_fetch_notices(self, build_note):
        self.expect_json_http({"results": [{"some": "thing"},
                                           {"another": "thing"}]})
        build_note.return_value = ['NOTICE!']

        notices = federalregister.fetch_notices(23, 1222)

        params = self.last_http_params()
        self.assertEqual(params['conditions[cfr][title]'], ['23'])
        self.assertEqual(params['conditions[cfr][part]'], ['1222'])

        self.assertEqual(['NOTICE!', 'NOTICE!'], notices)

    def test_meta_data_okay(self):
        """Successfully returns the appropriate JSON"""
        self.expect_json_http({"some": "value"},
                              uri=re.compile(".*/articles/1234-56"))

        self.assertEqual({"some": "value"},
                         federalregister.meta_data("1234-56"))

    def test_meta_data_passes_fields(self):
        """If a fields param is provided, it should be sent"""
        self.expect_json_http({"some": "value"},
                              uri=re.compile(".*/articles/1234-56"))

        federalregister.meta_data("1234-56", ['field1', 'field2', 'field3'])
        params = self.last_http_params()
        self.assertEqual(params['fields[]'], ['field1', 'field2', 'field3'])

    def test_meta_data_404(self):
        """If a document isn't present, expect an exception"""
        self.expect_json_http(status=404)
        self.assertRaises(Exception, federalregister.meta_data, 'doc-num')
