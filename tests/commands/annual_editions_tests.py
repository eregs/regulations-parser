from datetime import date, timedelta

import click
import pytest
from django.utils import timezone
from mock import Mock

from regparser.commands import annual_editions
from regparser.index import dependency, entry
from regparser.tree.struct import Node
from regparser.web.index.models import Entry as DBEntry
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile


@pytest.mark.django_db
def test_last_versions_raises_exception():
    """If there are no versions available, we should receive an exception"""
    with pytest.raises(click.UsageError):
        list(annual_editions.last_versions('12', '1000'))


@pytest.mark.django_db
def test_last_versions_multiple_versions(monkeypatch):
    """If multiple versions affect the same annual edition, we should only
    receive the last"""
    monkeypatch.setattr(annual_editions.annual, 'find_volume', Mock())
    annual_editions.annual.find_volume.return_value = True
    entry.Version('12', '1000', '1111').write(b'')
    CFRVersion.objects.create(
        identifier='1111', effective=date(2000, 12, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )
    entry.Version('12', '1000', '2222').write(b'')
    CFRVersion.objects.create(
        identifier='2222', effective=date(2000, 12, 2), fr_volume=1,
        fr_page=2, cfr_title=12, cfr_part=1000
    )
    entry.Version('12', '1000', '3333').write(b'')
    CFRVersion.objects.create(
        identifier='3333', effective=date(2001, 12, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )

    results = list(annual_editions.last_versions(12, 1000))
    assert results == [annual_editions.LastVersionInYear('2222', 2001),
                       annual_editions.LastVersionInYear('3333', 2002)]


@pytest.mark.django_db
def test_last_versions_not_printed(monkeypatch):
    """We should only find the annual editions which have been published
    already"""
    # 2001 exists; no other years do
    monkeypatch.setattr(annual_editions.annual, 'find_volume', Mock())
    annual_editions.annual.find_volume = lambda year, title, part: year == 2001
    entry.Version('12', '1000', '1111').write(b'')
    CFRVersion.objects.create(
        identifier='1111', effective=date(2000, 12, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )
    entry.Version('12', '1000', '2222').write(b'')
    CFRVersion.objects.create(
        identifier='2222', effective=date(2001, 12, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )

    results = list(annual_editions.last_versions(12, 1000))
    assert results == [annual_editions.LastVersionInYear('1111', 2001)]


@pytest.mark.django_db
def test_process_if_needed_missing_dependency_error():
    """If the annual XML or version isn't present, we should see a dependency
    error."""
    last_versions = [annual_editions.LastVersionInYear('1111', 2000)]

    with pytest.raises(dependency.Missing):
        annual_editions.process_if_needed('12', '1000', last_versions)

    entry.Version('12', '1000', '1111').write(b'')
    CFRVersion.objects.create(
        identifier='1111', effective=date(2000, 1, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )

    with pytest.raises(dependency.Missing):
        annual_editions.process_if_needed('12', '1000', last_versions)


@pytest.mark.django_db
def test_process_if_needed_missing_writes(monkeypatch):
    """If output isn't already present, we should process. If it is present,
    we don't need to, unless a dependency has changed."""
    monkeypatch.setattr(annual_editions, 'gpo_cfr', Mock())
    build_tree = annual_editions.gpo_cfr.builder.build_tree
    build_tree.return_value = Node()
    last_versions = [annual_editions.LastVersionInYear('1111', 2000)]
    entry.Version('12', '1000', '1111').write(b'')
    CFRVersion.objects.create(
        identifier='1111', effective=date(2000, 1, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )
    entry.Entry('annual', '12', '1000', 2000).write(b'')
    SourceFile.objects.create(
        collection=SourceCollection.annual.name,
        file_name=SourceCollection.annual.format(12, 1000, 2000),
        contents=b'<ROOT/>'
    )

    annual_editions.process_if_needed('12', '1000', last_versions)
    assert build_tree.called

    build_tree.reset_mock()
    entry.Entry('tree', '12', '1000', '1111').write(b'tree-here')
    annual_editions.process_if_needed('12', '1000', last_versions)
    assert not build_tree.called

    # Simulate a change to an input file
    label_id = str(entry.Annual(12, 1000, 2000))
    new_time = timezone.now() + timedelta(hours=1)
    DBEntry.objects.filter(label_id=label_id).update(modified=new_time)
    annual_editions.process_if_needed('12', '1000', last_versions)
    assert build_tree.called
