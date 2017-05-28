from hashlib import sha256
from os import path as ospath
from random import choice
from string import hexdigits
from tempfile import NamedTemporaryFile
from uuid import uuid4

import pytest
from mock import Mock, patch
from rest_framework.test import APITestCase
from six.moves.urllib.parse import urlparse

from regparser.web.jobs.models import job_status_values
from regparser.web.jobs.utils import (create_status_url, eregs_site_api_url,
                                      file_url)
from regparser.web.jobs.views import FileUploadView as PatchedFileUploadView
from regparser.web.settings import parser as settings

fake_pipeline_id = uuid4()


def _fake_redis_job(cmd, args, timeout=60*30, result_ttl=-1, depends_on=None):
    return Mock(id=fake_pipeline_id)


def _fake_redis_queue():
    return Mock(fetch_job=Mock(return_value=None))


@pytest.fixture
def tmp_media_root(tmpdir, settings):
    """For each test, create a temporary directory where its media (including
    any uploaded files) will be stored. The `tmpdir` fixture creates and tears
    down a temporary directory; the `settings` fixture allows us to easily set
    (and automatically unset) any Django setting"""
    settings.MEDIA_ROOT = str(tmpdir)


@patch("django_rq.enqueue", _fake_redis_job)
@patch("django_rq.get_queue", _fake_redis_queue)
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
        return self.client.post("/rp/jobs/regulations/", data, format="json")

    def _stock_response_check(self, expected, actual):
        """
        Since we're using a lot of fake values, the tests for them will always
        be the same.
        """
        for key in expected:
            self.assertEqual(expected[key], actual[key])
        self.assertIn(actual["status"], job_status_values)

    def _create_ints(self):
        data = {
            "cfr_title": 0,
            "cfr_part": 0,
            "notification_email": "test@example.com"
        }
        response = self._postjson(data)
        return (data, response)

    def test_create_ints(self):
        data, response = self._create_ints()

        expected = dict(self.defaults)
        expected.update({k: data[k] for k in data})
        expected["url"] = create_status_url(
            fake_pipeline_id, sub_path="regulations/")
        self._stock_response_check(expected, response.data)
        return expected

    def test_create_strings(self):
        data = {
            "cfr_title": "0",
            "cfr_part": "0",
            "notification_email": "test@example.com"
        }
        response = self._postjson(data)

        expected = dict(self.defaults)
        expected.update({k: data[k] for k in data})
        # Even if the input is a str, the return values should be ints:
        expected["cfr_title"] = int(expected["cfr_title"])
        expected["cfr_part"] = int(expected["cfr_part"])
        expected["url"] = create_status_url(
            fake_pipeline_id, sub_path="regulations/")
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

        response = self.client.get("/rp/jobs/regulations/", format="json")
        self.assertEqual(0, len(response.data))

    def test_create_and_read(self):
        expected = self._create_ints()[1].data

        url = urlparse(expected["url"])
        response = self.client.get(url.path, format="json")
        self._stock_response_check(expected, response.data)

        response = self.client.get("/rp/jobs/regulations/", format="json")
        self.assertEqual(1, len(response.data))
        self._stock_response_check(expected, response.data[0])

    def test_create_delete_and_read(self):
        expected = self._create_ints()[1].data

        url = urlparse(expected["url"])
        response = self.client.delete(url.path, format="json")
        self.assertEqual(204, response.status_code)

        response = self.client.get(url.path, format="json")
        self.assertEqual(404, response.status_code)

        response = self.client.get("/rp/jobs/regulations/", format="json")
        self.assertEqual(0, len(response.data))


@pytest.mark.usefixtures("tmp_media_root")
class RegulationFileTestCase(APITestCase):
    def __init__(self, *args, **kwargs):
        self.file_contents = "123"
        self.hashed_contents = None
        super(RegulationFileTestCase, self).__init__(*args, **kwargs)

    def get_hashed_contents(self):
        if self.hashed_contents is None:
            self.hashed_contents = sha256(self.file_contents.encode(
                "utf-8")).hexdigest()
        return self.hashed_contents

    def test_create_file(self):
        with NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
            tmp.write(self.file_contents.encode("utf-8"))
            tmp_name = ospath.split(tmp.name)[-1]
            tmp.seek(0)
            response = self.client.post(
                "/rp/jobs/files/", {"file": tmp})
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
                "/rp/jobs/files/", {"file": tmp})
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
                    "/rp/jobs/files/", {"file": tmp})
            self.assertEquals(201, response.status_code)

            with NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
                contents = "123" * 11
                tmp.write(contents.encode("utf-8"))
                tmp.seek(0)
                response = self.client.post(
                    "/rp/jobs/files/", {"file": tmp})
            self.assertEquals(400, response.status_code)
            self.assertEquals("File too large (10-byte limit).",
                              response.data["error"])

    def test_create_and_read_and_delete(self):
        expected = self.test_create_file().data
        url = urlparse(expected["url"])
        response = self.client.get(url.path)
        contents = response.content.decode("utf-8")
        self.assertEquals(self.file_contents, contents)

        response = self.client.get("/rp/jobs/files/", format="json")
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

        response = self.client.get("/rp/jobs/files/", format="json")
        data = response.data
        self.assertEquals(0, len(data))


@pytest.mark.usefixtures("tmp_media_root")
@patch("django_rq.enqueue", _fake_redis_job)
@patch("django_rq.get_queue", _fake_redis_queue)
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
            response = self.client.post("/rp/jobs/files/", {"file": tmp})
        return response.data

    def _postjson(self, data):
        return self.client.post("/rp/jobs/notices/", data,
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

        expected = dict(self.defaults)
        expected.update({k: data[k] for k in data})
        expected["url"] = create_status_url(
            fake_pipeline_id, sub_path="notices/")
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

        response = self.client.get("/rp/jobs/notices/", format="json")
        self.assertEqual(1, len(response.data))
        self._stock_response_check(expected, response.data[0])

        response = self.client.delete(url.path, format="json")
        self.assertEqual(204, response.status_code)

        response = self.client.get(url.path, format="json")
        self.assertEqual(404, response.status_code)

        response = self.client.get("/rp/jobs/notices/", format="json")
        self.assertEqual(0, len(response.data))


@patch.object(settings, "CANONICAL_HOSTNAME", "http://domain.tld")
def test_create_status_url():
    domain = "http://domain.tld"
    urlpath = "/rp/jobs/"
    hexes = ["".join([choice(hexdigits) for i in range(32)]) for j in range(6)]

    def _check(port=None):
        for hx in hexes:
            url = urlparse(create_status_url(hx))
            assert domain == "{0}://{1}".format(url.scheme, url.hostname)
            if port is None:
                assert url.port is port
            else:
                assert url.port == port
            assert "{0}{1}/".format(urlpath, hx) == url.path

            url = urlparse(create_status_url(
                hx, sub_path="{0}/".format(hx[:10])))
            assert domain == "{0}://{1}".format(url.scheme, url.hostname)
            if port is None:
                assert url.port is port
            else:
                assert url.port == port
            assert "{0}{1}{2}/".format(
                urlpath, "{0}/".format(hx[:10]), hx) == url.path

    with patch.object(settings, "CANONICAL_PORT", "2323"):
        _check(port=2323)

    for port in ("80", "443", ""):
        with patch.object(settings, "CANONICAL_PORT", port):
            _check()

    with pytest.raises(ValueError) as err:
        create_status_url("something", "something-without-a-slash")

    assert isinstance(err.value, ValueError)


@patch.object(settings, "CANONICAL_HOSTNAME", "http://domain.tld")
def test_file_url():
    urlpath = "/rp/jobs/files/"
    domain = "http://domain.tld"
    hexes = ["".join([choice(hexdigits) for i in range(32)]) for j in range(6)]

    with patch.object(settings, "CANONICAL_PORT", "2323"):
        for hx in hexes:
            assert file_url(hx) == "{0}:2323{1}{2}/".format(
                domain, urlpath, hx)

    for port in ("80", "443", ""):
        with patch.object(settings, "CANONICAL_PORT", port):
            for hx in hexes:
                assert file_url(hx) == "{0}{1}{2}/".format(domain, urlpath, hx)
