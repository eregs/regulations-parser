from datetime import date

import pytest

from regparser.commands import sxs_layers
from regparser.index import dependency, entry
from regparser.web.index.models import CFRVersion


def create_versions():
    """Generate some dummy data"""
    entry.Version(11, 222, 'aaa').write(b'')
    CFRVersion.objects.create(
        identifier='aaa', effective=date(2002, 2, 2), fr_volume=2, fr_page=2,
        cfr_title=11, cfr_part=222)
    entry.Version(11, 222, 'bbb').write(b'')
    CFRVersion.objects.create(
        identifier='bbb', effective=date(2001, 1, 1), fr_volume=1, fr_page=1,
        cfr_title=11, cfr_part=222)
    entry.Version(11, 222, 'ccc').write(b'')
    CFRVersion.objects.create(
        identifier='ccc', effective=date(2003, 3, 3), fr_volume=3, fr_page=3,
        cfr_title=11, cfr_part=222)


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
    entry.Entry('notice_xml', 'aaa').write(b'')
    entry.Entry('notice_xml', 'bbb').write(b'')
    with pytest.raises(dependency.Missing):
        sxs_layers.is_stale(11, 222, 'aaa')

    entry.Entry('tree', 11, 222, 'bbb').write(b'')   # Wrong tree
    with pytest.raises(dependency.Missing):
        sxs_layers.is_stale(11, 222, 'aaa')

    entry.Entry('tree', 11, 222, 'aaa').write(b'')
    assert sxs_layers.is_stale(11, 222, 'aaa')
