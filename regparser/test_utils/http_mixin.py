import json
import re

import httpretty


class HttpMixin(object):
    """Mixin for tests which perform mocked http interactions"""
    def setUp(self):
        super(HttpMixin, self).setUp()
        httpretty.enable()

    def tearDown(self):
        super(HttpMixin, self).tearDown()
        httpretty.disable()
        httpretty.reset()

    def expect_json_http(self, json_dict=None, **kwargs):
        """Wraps httpretty.register_uri with some defaults for JSON"""
        if json_dict is None:
            json_dict = {"key": "value"}
        kwargs['body'] = json.dumps(json_dict)
        kwargs['content_type'] = 'text/json'
        self.expect_http(**kwargs)

    def expect_xml_http(self, xml_str=None, **kwargs):
        """Wraps httpretty.register_uri with some defaults for XML"""
        if xml_str is None:
            xml_str = '<ROOT></ROOT>'
        kwargs['body'] = xml_str
        kwargs['content_type'] = 'text/xml'
        self.expect_http(**kwargs)

    def expect_http(self, **kwargs):
        """Wraps httpretty.register_uri with some defaults"""
        kwargs['body'] = kwargs.get('body', b'')
        kwargs['content_type'] = kwargs.get('content_type',
                                            'application/octet-stream')
        kwargs['method'] = kwargs.get('method', httpretty.GET)
        # Default to catching all requests
        kwargs['uri'] = kwargs.get('uri', re.compile(".*"))
        httpretty.register_uri(**kwargs)

    def last_http_params(self):
        return httpretty.last_request().querystring

    def last_http_headers(self):
        return httpretty.last_request().headers

    def last_http_body(self):
        return httpretty.last_request().parsed_body
