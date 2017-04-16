from datetime import date

import click
import pytest
from mock import Mock, call
from model_mommy import mommy

from regparser.commands import annual_editions
from regparser.tree.struct import Node
from regparser.web.index.models import (CFRVersion, Document, SourceCollection,
                                        SourceFile)


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
    v1, v2, v3 = mommy.make(
        CFRVersion, _quantity=3, effective=date(2000, 12, 1), fr_volume=1,
        fr_page=1, cfr_title=12, cfr_part=1000
    )
    v2.effective = date(2000, 12, 2)
    v2.save()
    v3.effective = date(2001, 12, 1)
    v3.save()

    results = list(annual_editions.last_versions(12, 1000))
    assert results == [v2, v3]


@pytest.mark.django_db
def test_last_versions_not_printed(monkeypatch):
    """We should only find the annual editions which have been published
    already"""
    # 2001 exists; no other years do
    monkeypatch.setattr(annual_editions.annual, 'find_volume', Mock())
    annual_editions.annual.find_volume = lambda year, title, part: year == 2001
    v1 = mommy.make(CFRVersion, cfr_title=12, cfr_part=1000,
                    effective=date(2000, 12, 1))
    mommy.make(CFRVersion, cfr_title=12, cfr_part=1000,
               effective=date(2001, 12, 1))

    results = list(annual_editions.last_versions(12, 1000))
    assert results == [v1]


@pytest.mark.django_db
def test_source_file_missing_dependency():
    """If the source XML isn't present, we should run a command to grab it"""
    ctx = Mock()

    def mock_invoke(command, cfr_title, cfr_part, year):
        file_name = SourceCollection.annual.format(cfr_title, cfr_part, year)
        mommy.make(SourceFile, collection=SourceCollection.annual.name,
                   file_name=file_name)
    ctx.invoke.side_effect = mock_invoke

    assert not SourceFile.objects.exists()
    annual_editions.source_file(ctx, 11, 222, 2010)

    assert SourceFile.objects.count() == 1
    assert ctx.invoke.call_args == call(
        annual_editions.fetch_annual_edition, 11, 222, 2010)

    annual_editions.source_file(ctx, 11, 222, 2010)
    assert SourceFile.objects.count() == 1      # doesn't change


@pytest.mark.django_db
def test_create_where_needed_writes(monkeypatch):
    """If don't have an appropriate Document, we create one"""
    monkeypatch.setattr(annual_editions, 'gpo_cfr', Mock())
    build_tree = annual_editions.gpo_cfr.builder.build_tree
    build_tree.return_value = Node()
    version = mommy.make(CFRVersion, effective=date(2000, 1, 1), cfr_title=12,
                         cfr_part=1000)
    SourceFile.objects.create(
        collection=SourceCollection.annual.name,
        file_name=SourceCollection.annual.format(12, 1000, 2000),
        contents=b'<ROOT/>'
    )

    assert not Document.objects.exists()
    annual_editions.create_where_needed(Mock(), '12', '1000', [version])
    assert build_tree.called
    assert Document.objects.count() == 1

    build_tree.reset_mock()
    annual_editions.create_where_needed(Mock(), '12', '1000', [version])
    assert not build_tree.called
    assert Document.objects.count() == 1
