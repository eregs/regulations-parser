import os

from click.testing import CliRunner
import pytest

from regparser.commands.clear import clear
from regparser.index import dependency, entry


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


def test_deletes_http_cache(tmpdir_setup):
    sqlite_filename = tmpdir_setup.REQUESTS_CACHE['cache_name'] + '.sqlite'
    open(sqlite_filename, 'w').close()
    assert os.path.exists(sqlite_filename)

    CliRunner().invoke(clear)
    assert not os.path.exists(sqlite_filename)


def test_deletes_index(tmpdir_setup):
    entry.Entry('aaa', 'bbb').write(b'ccc')
    entry.Entry('bbb', 'ccc').write(b'ddd')
    assert 1 == len(entry.Entry("aaa"))
    assert 1 == len(entry.Entry("bbb"))

    CliRunner().invoke(clear)
    assert 0 == len(entry.Entry("aaa"))
    assert 0 == len(entry.Entry("bbb"))


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

    expected = set(['top-level-file', 'root', 'other-root'])
    assert set(entry.Entry()) == expected
    assert set(entry.Entry('root')) == set(['othersub', 'aaa'])
    assert set(entry.Entry('other-root')) == set(['aaa'])
