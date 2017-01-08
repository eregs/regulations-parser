import os

import httpretty
import pytest
from click.testing import CliRunner

from regparser.commands.clear import clear
from regparser.index import dependency, entry
from regparser.index.http_cache import http_client
from regparser.test_utils.http_mixin import http_pretty_fixture

http_pretty = http_pretty_fixture


@pytest.fixture
def tmpdir_setup(tmpdir, settings):
    """Put the index files in a temporary location"""
    settings.EREGS_INDEX_ROOT = str(tmpdir)
    settings.REQUESTS_CACHE.update(
        backend='sqlite', cache_name=str(tmpdir.join("http_cache")))
    return settings


def test_no_errors_when_clear(tmpdir_setup):
    """Should raise no errors when no cached files are present"""
    CliRunner().invoke(clear)


@pytest.mark.django_db
def test_deletes_http_cache(http_pretty, tmpdir_setup):
    assert len(http_client().cache.responses) == 0

    httpretty.register_uri(httpretty.GET, 'http://example.com')
    http_client().get('http://example.com')
    assert len(http_client().cache.responses) == 1

    CliRunner().invoke(clear)
    assert len(http_client().cache.responses) == 0


@pytest.mark.django_db
def test_deletes_index(tmpdir_setup):
    entry.Entry('aaa', 'bbb').write(b'ccc')
    entry.Entry('bbb', 'ccc').write(b'ddd')
    assert 1 == len(list(entry.Entry("aaa").sub_entries()))
    assert 1 == len(list(entry.Entry("bbb").sub_entries()))

    CliRunner().invoke(clear)
    assert [] == list(entry.Entry().sub_entries())


@pytest.mark.django_db
def test_deletes_dependencies(tmpdir_setup):
    graph = dependency.Graph()
    graph.add('a', 'b')
    assert len(graph.dependencies('a')) == 1
    graph = dependency.Graph()
    assert len(graph.dependencies('a')) == 1

    CliRunner().invoke(clear)
    graph = dependency.Graph()
    assert len(graph.dependencies('a')) == 0


@pytest.mark.django_db
def test_deletes_can_be_focused(tmpdir_setup):
    """If params are provided to delete certain directories, only those
    directories should get removed"""
    to_delete = ['delroot/aaa/bbb', 'delroot/aaa/ccc',
                 'root/delsub/aaa', 'root/delsub/bbb']
    to_keep = ['root/othersub/aaa', 'root/aaa',
               'top-level-file', 'other-root/aaa']

    for path in to_delete + to_keep:
        entry.Entry(*path.split('/')).write(b'')

    CliRunner().invoke(clear, ['delroot', 'root/delsub'])

    assert {os.sep.join(c.path)
            for c in entry.Entry().sub_entries()} == set(to_keep)
