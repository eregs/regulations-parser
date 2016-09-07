from hashlib import md5
from mock import patch
from os import path as ospath
from random import choice
from regparser.web.jobs.models import job_status_values
from regparser.web.jobs.utils import (
    eregs_site_api_url,
    file_url,
    status_url
)
from regparser.web.jobs.views import FileUploadView as PatchedFileUploadView
from rest_framework.test import APITestCase
from string import hexdigits
from tempfile import NamedTemporaryFile
from uuid import uuid4

import pytest
import settings

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

fake_pipeline_id = uuid4()
fake_email_id = uuid4()


def fake_getter(attrname):
    return attrname


def fake_add_redis_data_to_job_data(job_data):
    return job_data


def fake_delete_eregs_job(job_id):
    return None


def fake_redis_job(args, timeout=60*30, result_ttl=-1):
    return type("FakeRedisJob", (object, ), {"id": fake_pipeline_id})


def fake_queue_email(job, statusurl, email_address):
    return fake_email_id


# Even though these functions are in the ``utils`` module, the code paths we're
# following mean we're encountering them in the ``views`` namespace:
@patch("regparser.web.jobs.views.add_redis_data_to_job_data",
       fake_add_redis_data_to_job_data)
@patch("regparser.web.jobs.views.delete_eregs_job", fake_delete_eregs_job)
@patch("regparser.web.jobs.views.queue_eregs_job", fake_redis_job)
@patch("regparser.web.jobs.views.queue_notification_email", fake_queue_email)
class PipelineJobTestCase(APITestCase):

    def __init__(self, *args, **kwargs):
        self.defaults = {
            "clear_cache": False,
            "destination": eregs_site_api_url,
            "use_uploaded_metadata": None,
            "use_uploaded_regulation": None,
            "regulation_url": "",
            "status": "received"
        }
        super(PipelineJobTestCase, self).__init__(*args, **kwargs)

    def _postjson(self, data):
        return self.client.post("/rp/job/pipeline/", data, format="json")

    def _stock_response_check(self, expected, actual):
        """
        Since we're using a lot of fake values, the tests for them will always
        be the same.
        """
        for key in expected:
            self.assertEqual(expected[key], actual[key])
        self.assertIn(actual["status"], job_status_values)

    def test_create_ints(self):
        data = {
            "cfr_title": 0,
            "cfr_part": 0,
            "notification_email": "test@example.com"
        }
        response = self._postjson(data)

        expected = {k: data[k] for k in data}
        expected.update(self.defaults)
        expected["url"] = status_url(fake_pipeline_id, sub_path="pipeline/")
        self._stock_response_check(expected, response.data)
        return expected

    def test_create_strings(self):
        data = {
            "cfr_title": "0",
            "cfr_part": "0",
            "notification_email": "test@example.com"
        }
        response = self._postjson(data)

        expected = {k: data[k] for k in data}
        expected.update(self.defaults)
        # Even if the input is a str, the return values should be ints:
        expected["cfr_title"] = int(expected["cfr_title"])
        expected["cfr_part"] = int(expected["cfr_part"])
        expected["url"] = status_url(fake_pipeline_id, sub_path="pipeline/")
        self._stock_response_check(expected, response.data)

    def test_create_with_missing_fields(self):
        data = {"cfr_part": "0"}
        response = self._postjson(data)

        self.assertEqual(400, response.status_code)
        self.assertEqual({"cfr_title": ["This field is required."]},
                         response.data)

        data = {"cfr_title": "0"}
        response = self._postjson(data)

        self.assertEqual(400, response.status_code)
        self.assertEqual({"cfr_part": ["This field is required."]},
                         response.data)

        response = self.client.get("/rp/job/pipeline/", format="json")
        self.assertEqual(0, len(response.data))

    def test_create_and_read(self):
        expected = self.test_create_ints()

        url = urlparse(expected["url"])
        response = self.client.get(url.path, format="json")
        self._stock_response_check(expected, response.data)

        response = self.client.get("/rp/job/pipeline/", format="json")
        self.assertEqual(1, len(response.data))
        self._stock_response_check(expected, response.data[0])

    def test_create_delete_and_read(self):
        expected = self.test_create_ints()

        url = urlparse(expected["url"])
        response = self.client.delete(url.path, format="json")
        self.assertEqual(204, response.status_code)

        response = self.client.get(url.path, format="json")
        self.assertEqual(404, response.status_code)

        response = self.client.get("/rp/job/pipeline/", format="json")
        self.assertEqual(0, len(response.data))


class RegulationFileTestCase(APITestCase):

    def __init__(self, *args, **kwargs):
        self.file_contents = "123"
        self.hashed_contents = None
        super(RegulationFileTestCase, self).__init__(*args, **kwargs)

    def get_hashed_contents(self):
        if self.hashed_contents is None:
            try:
                self.hashed_contents = md5(self.file_contents.encode(
                    "utf-8")).hexdigest()
            except AttributeError:
                self.hashed_contents = md5(self.file_contents).hexdigest()
        return self.hashed_contents

    def test_create_file(self):
        with NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
            tmp.write(self.file_contents.encode("utf-8"))
            tmp_name = ospath.split(tmp.name)[-1]
            tmp.seek(0)
            response = self.client.post(
                "/rp/job/upload/", {"file": tmp})
        self.assertEquals(201, response.status_code)
        data = response.data
        self.assertEquals(self.get_hashed_contents(), data["hexhash"])
        self.assertEquals(tmp_name, data["filename"])
        self.assertEquals("File contents not shown.", data["contents"])
        self.assertEquals(file_url(self.get_hashed_contents()), data["url"])
        return response

    def test_reject_duplicates(self):
        self.test_create_file()
        with NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
            tmp.write(self.file_contents.encode("utf-8"))
            tmp.seek(0)
            response = self.client.post(
                "/rp/job/upload/", {"file": tmp})
        self.assertEquals(400, response.status_code)
        self.assertIn("error", response.data)
        self.assertEquals("File already present.", response.data["error"])

    def test_reject_large(self):
        with patch("regparser.web.jobs.views.FileUploadView",
                   new=PatchedFileUploadView) as p:
            p.size_limit = 10
            with NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
                tmp.write(self.file_contents.encode("utf-8"))
                tmp.seek(0)
                response = self.client.post(
                    "/rp/job/upload/", {"file": tmp})
            self.assertEquals(201, response.status_code)

            with NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
                contents = "123" * 11
                tmp.write(contents.encode("utf-8"))
                tmp.seek(0)
                response = self.client.post(
                    "/rp/job/upload/", {"file": tmp})
            self.assertEquals(400, response.status_code)
            self.assertEquals("File too large (10-byte limit).",
                              response.data["error"])

    def test_create_and_read_and_delete(self):
        expected = self.test_create_file().data
        url = urlparse(expected["url"])
        response = self.client.get(url.path)
        contents = response.content.decode("utf-8")
        self.assertEquals(self.file_contents, contents)

        response = self.client.get("/rp/job/upload/", format="json")
        self.assertEquals(1, len(response.data))
        data = response.data[0]
        self.assertEquals("File contents not shown.", data["contents"])
        self.assertEquals(expected["file"], data["file"])
        self.assertEquals(expected["filename"], data["filename"])
        self.assertEquals(self.get_hashed_contents(), data["hexhash"])
        self.assertEquals(url.path, urlparse(data["url"]).path)

        response = self.client.delete(url.path)
        self.assertEqual(204, response.status_code)

        response = self.client.get(url.path)
        self.assertEqual(404, response.status_code)

        response = self.client.get("/rp/job/upload/", format="json")
        data = response.data
        self.assertEquals(0, len(data))


@patch("regparser.web.jobs.views.add_redis_data_to_job_data",
       fake_add_redis_data_to_job_data)
@patch("regparser.web.jobs.views.delete_eregs_job", fake_delete_eregs_job)
@patch("regparser.web.jobs.views.queue_eregs_job", fake_redis_job)
@patch("regparser.web.jobs.views.queue_notification_email", fake_queue_email)
class ProposalPipelineTestCase(APITestCase):

    def __init__(self, *args, **kwargs):
        self.defaults = {
            "clear_cache": False,
            "destination": eregs_site_api_url,
            "only_latest": True,
            "use_uploaded_metadata": None,
            "use_uploaded_regulation": None,
            "regulation_url": "",
            "status": "received"
        }
        self.file_contents = "456"
        super(ProposalPipelineTestCase, self).__init__(*args, **kwargs)

    def _create_file(self):
        with NamedTemporaryFile(suffix=".xml") as tmp:
            tmp.write(self.file_contents.encode("utf-8"))
            tmp.seek(0)
            response = self.client.post("/rp/job/upload/", {"file": tmp})
        return response.data

    def _postjson(self, data):
        return self.client.post("/rp/job/proposal-pipeline/", data,
                                format="json")

    def _stock_response_check(self, expected, actual):
        """
        Since we're using a lot of fake values, the tests for them will always
        be the same.
        """
        for key in expected:
            self.assertEqual(expected[key], actual[key])
        self.assertIn(actual["status"], job_status_values)

    def test_create(self):
        file_data = self._create_file()
        data = {
            "file_hexhash": file_data["hexhash"],
            "notification_email": "test@example.com"
        }
        response = self._postjson(data)
        expected = {k: data[k] for k in data}
        expected.update(self.defaults)
        expected["url"] = status_url(fake_pipeline_id,
                                     sub_path="proposal-pipeline/")
        self._stock_response_check(expected, response.data)
        return expected

    def test_create_with_missing_fields(self):
        data = {"notification_email": "test@example.com"}
        response = self._postjson(data)

        self.assertEqual(400, response.status_code)
        self.assertEqual({"file_hexhash": ["This field is required."]},
                         response.data)

    def test_create_and_read_and_delete(self):
        expected = self.test_create()

        url = urlparse(expected["url"])
        response = self.client.get(url.path, format="json")
        self._stock_response_check(expected, response.data)

        response = self.client.get("/rp/job/proposal-pipeline/", format="json")
        self.assertEqual(1, len(response.data))
        self._stock_response_check(expected, response.data[0])

        response = self.client.delete(url.path, format="json")
        self.assertEqual(204, response.status_code)

        response = self.client.get(url.path, format="json")
        self.assertEqual(404, response.status_code)

        response = self.client.get("/rp/job/proposal-pipeline/", format="json")
        self.assertEqual(0, len(response.data))


@patch.object(settings, "CANONICAL_HOSTNAME", "http://domain.tld")
def test_status_url():
    domain = "http://domain.tld"
    urlpath = "/rp/job/"
    hexes = ["".join([choice(hexdigits) for i in range(32)]) for j in range(6)]

    def _check(port=None):
        for hx in hexes:
            url = urlparse(status_url(hx))
            assert domain == "%s://%s" % (url.scheme, url.hostname)
            if port is None:
                assert url.port is port
            else:
                assert url.port == port
            assert "%s%s/" % (urlpath, hx) == url.path

            url = urlparse(status_url(hx, sub_path="%s/" % hx[:10]))
            assert domain == "%s://%s" % (url.scheme, url.hostname)
            if port is None:
                assert url.port is port
            else:
                assert url.port == port
            assert "%s%s%s/" % (urlpath, "%s/" % hx[:10], hx) == url.path

    with patch.object(settings, "CANONICAL_PORT", "2323"):
        _check(port=2323)

    with patch.object(settings, "CANONICAL_PORT", "80"):
        _check()

    with patch.object(settings, "CANONICAL_PORT", ""):
        _check()

    with pytest.raises(ValueError) as err:
        status_url("something", "something-without-a-slash")

    assert isinstance(err.value, ValueError)


@patch.object(settings, "CANONICAL_HOSTNAME", "http://domain.tld")
def test_file_url():
    urlpath = "/rp/job/upload/"
    domain = "http://domain.tld"
    hexes = ["".join([choice(hexdigits) for i in range(32)]) for j in range(6)]

    with patch.object(settings, "CANONICAL_PORT", "2323"):
        for hx in hexes:
            assert file_url(hx) == "%s:2323%s%s/" % (domain, urlpath, hx)

    with patch.object(settings, "CANONICAL_PORT", "80"):
        for hx in hexes:
            assert file_url(hx) == "%s%s%s/" % (domain, urlpath, hx)

    with patch.object(settings, "CANONICAL_PORT", ""):
        for hx in hexes:
            assert file_url(hx) == "%s%s%s/" % (domain, urlpath, hx)
