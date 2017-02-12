from datetime import date

import pytest

from regparser.commands import sxs_layers
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.notice.citation import Citation


def create_versions():
    """Generate some dummy data"""
    entry.Version(11, 222, 'aaa').write(
        Version('aaa', date(2002, 2, 2), Citation(2, 2)))
    entry.Version(11, 222, 'bbb').write(
        Version('bbb', date(2001, 1, 1), Citation(1, 1)))
    entry.Version(11, 222, 'ccc').write(
        Version('ccc', date(2003, 3, 3), Citation(3, 3)))


@pytest.mark.django_db
def test_previous_sxs():
    """Should return SxS in version order; should only include SxS until
    the stop_version specified"""
    create_versions()
    assert [s.path[0] for s in sxs_layers.previous_sxs(11, 222, 'aaa')] == [
        'bbb', 'aaa']
    assert [s.path[0] for s in sxs_layers.previous_sxs(11, 222, 'bbb')] == [
        'bbb']
    assert [s.path[0] for s in sxs_layers.previous_sxs(11, 222, 'ccc')] == [
        'bbb', 'aaa', 'ccc']


@pytest.mark.django_db
def test_is_stale():
    """We should raise dependency exceptions when necessary files haven't been
    processed. We need SxS entries _and_ the relevant tree"""
    with pytest.raises(dependency.Missing):
        sxs_layers.is_stale(11, 222, 'aaa')

    create_versions()
    entry.Entry('sxs', 'aaa').write(b'')
    entry.Entry('sxs', 'bbb').write(b'')
    with pytest.raises(dependency.Missing):
        sxs_layers.is_stale(11, 222, 'aaa')

    entry.Entry('tree', 11, 222, 'bbb').write(b'')   # Wrong tree
    with pytest.raises(dependency.Missing):
        sxs_layers.is_stale(11, 222, 'aaa')

    entry.Entry('tree', 11, 222, 'aaa').write(b'')
    assert sxs_layers.is_stale(11, 222, 'aaa')
