import json
from datetime import date
from random import randint

import pytest
from mock import Mock

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
    annual_version.create_version_entry_if_needed(Volume(2010, 20, 1), 1001)
    version = entry.Version(20, 1001, '2010-annual-1001').read()
    assert version.effective == date(2010, 4, 1)
    assert version.published == date(2010, 4, 1)
