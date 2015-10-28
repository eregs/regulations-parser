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
        """Wraps httpretty.register_uri with some defaults"""
        if json_dict is None:
            json_dict = {"key": "value"}
        kwargs['body'] = json.dumps(json_dict)
        kwargs['content_type'] = 'text/json'
        kwargs['method'] = kwargs.get('method', httpretty.GET)
        # Default to catching all requests
        kwargs['uri'] = kwargs.get('uri', re.compile(".*"))
        httpretty.register_uri(**kwargs)

    def last_http_params(self):
        return httpretty.last_request().querystring

    def last_http_headers(self):
        return httpretty.last_request().headers.dict

    def last_http_body(self):
        return httpretty.last_request().parsed_body
