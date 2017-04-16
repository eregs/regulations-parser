from datetime import date
from random import randint

import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from mock import Mock, call
from model_mommy import mommy

from regparser.commands import annual_version
from regparser.history.annual import Volume
from regparser.notice.xml import NoticeXML, TitlePartsRef
from regparser.web.index.models import (CFRVersion, Document, SourceCollection,
                                        SourceFile)


@pytest.mark.django_db
def test_process_creation(monkeypatch):
    """If no tree is present, we should build one"""
    title, part, year = randint(1, 999), randint(1, 999), randint(2000, 2020)
    version_id = '{0}-annual-{1}'.format(year, part)
    source = SourceFile.objects.create(
        collection=SourceCollection.annual.name,
        file_name=SourceCollection.annual.format(title, part, year),
        contents=b'<ROOT />'
    )
    monkeypatch.setattr(annual_version, 'encoded_tree',
                        Mock(return_value=b'tree-here'))

    assert Document.objects.count() == 0
    annual_version.create_where_needed(Volume(year, title, 1), part, source)
    assert Document.objects.count() == 1

    notice = NoticeXML.from_db(version_id)
    assert notice.version_id == version_id
    assert notice.cfr_refs == [TitlePartsRef(title, [part])]


@pytest.mark.django_db
def test_create_version(monkeypatch):
    """Creates a version associated with the part and year"""
    monkeypatch.setattr(annual_version, 'create_notice_if_needed', Mock())
    monkeypatch.setattr(annual_version, 'create_document_if_needed', Mock())
    source = mommy.make(SourceFile)

    annual_version.create_where_needed(Volume(2010, 20, 5), 1001, source)
    version = CFRVersion.objects.get()
    assert version.effective == date(2010, 4, 1)
    assert version.fr_volume == 1
    assert version.fr_page == 1
    assert version.source == source


@pytest.fixture
def setup_for_2001(monkeypatch):
    monkeypatch.setattr(annual_version, 'find_volume', Mock())
    monkeypatch.setattr(annual_version, 'source_file', Mock())
    monkeypatch.setattr(annual_version, 'create_where_needed', Mock())
    with freeze_time('2001-01-01'):
        yield


@pytest.mark.usefixtures('setup_for_2001')
def test_current_year_exists():
    """If no parameter is passed, we should expect the current year to be
    used."""
    CliRunner().invoke(annual_version.annual_version, ['1', '2'])
    assert annual_version.find_volume.call_args_list == [call(2001, 1, 2)]


@pytest.mark.usefixtures('setup_for_2001')
def test_current_year_not_exists():
    """If no parameter is passed, we should expect the current year to be
    used. If that annual edition doesn't exist, we should try one year
    previous."""
    annual_version.find_volume.side_effect = (None, Mock())
    CliRunner().invoke(annual_version.annual_version, ['1', '2'])
    assert annual_version.find_volume.call_args_list == [call(2001, 1, 2),
                                                         call(2000, 1, 2)]


@pytest.mark.usefixtures('setup_for_2001')
def test_specific_year():
    """If a specific year is requested, it should be used, regardless of the
    present date"""
    CliRunner().invoke(annual_version.annual_version,
                       ['1', '2', '--year', '1999'])
    assert annual_version.find_volume.call_args_list == [call(1999, 1, 2)]
