import json
from datetime import date
from random import randint

import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from mock import Mock, call

from regparser.commands import annual_version
from regparser.history.annual import Volume
from regparser.index import entry
from regparser.notice.xml import TitlePartsRef


@pytest.mark.django_db
def test_process_creation(monkeypatch):
    """If no tree is present, we should build one"""
    title, part, year = randint(1, 999), randint(1, 999), randint(2000, 2020)
    version_id = '{0}-annual-{1}'.format(year, part)
    monkeypatch.setattr(annual_version, 'builder', Mock())

    entry.Entry('annual', title, part, year).write(b'<ROOT />')

    annual_version.builder.build_tree.return_value = {'my': 'tree'}
    annual_version.process_if_needed(Volume(year, title, 1), part)
    tree = entry.Entry('tree', title, part, version_id).read()
    assert json.loads(tree.decode('utf-8')) == {'my': 'tree'}

    notice = entry.Notice(version_id).read()
    assert notice.version_id == version_id
    assert notice.cfr_refs == [TitlePartsRef(title, [part])]


@pytest.mark.django_db
def test_process_no_need_to_create():
    """If everything is up to date, we don't need to build new versions"""
    title, part, year = randint(1, 999), randint(1, 999), randint(2000, 2020)
    annual = entry.Entry('annual', title, part, year)
    tree = entry.Entry('tree', title, part,
                       '{0}-annual-{1}'.format(year, part))
    annual.write(b'ANNUAL')
    tree.write(b'TREE')

    annual_version.process_if_needed(Volume(year, title, 1), part)

    # didn't change
    assert annual.read() == b'ANNUAL'
    assert tree.read() == b'TREE'


@pytest.mark.django_db
def test_create_version():
    """Creates a version associated with the part and year"""
    vol_num = randint(1, 99)
    annual_version.create_version_entry_if_needed(
        Volume(2010, 20, vol_num), 1001)
    version = entry.Version(20, 1001, '2010-annual-1001').read()
    assert version.effective == date(2010, 4, 1)
    assert version.fr_citation.volume == vol_num
    assert version.fr_citation.page == 1


@pytest.fixture
def setup_for_2001(monkeypatch):
    monkeypatch.setattr(annual_version, 'find_volume', Mock())
    monkeypatch.setattr(annual_version, 'create_version_entry_if_needed',
                        Mock())
    monkeypatch.setattr(annual_version, 'process_if_needed', Mock())
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
