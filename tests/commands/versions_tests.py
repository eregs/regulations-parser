from datetime import date, timedelta

import pytest
from django.utils import timezone
from mock import Mock

from regparser.commands import versions
from regparser.history.delays import FRDelay
from regparser.index import dependency, entry
from regparser.notice.citation import Citation
from regparser.web.index.models import Entry as DBEntry


@pytest.mark.django_db
def test_fetch_version_ids_no_local(monkeypatch):
    """If there are no local copies, the document numbers found in the FR
    notices should be passed through"""
    monkeypatch.setattr(versions, 'fetch_notice_json', Mock(return_value=[
        {'document_number': '1', 'full_text_xml_url': 'somewhere'},
        {'document_number': '22', 'full_text_xml_url': 'somewhere'}
    ]))
    path = entry.Entry("path")
    assert ['1', '22'] == versions.fetch_version_ids('title', 'part', path)


@pytest.mark.django_db
def test_fetch_version_ids_local(monkeypatch):
    """If a notice is split into multiple entries locally, a single document
    number might result in multiple version ids"""
    monkeypatch.setattr(versions, 'fetch_notice_json', Mock(return_value=[
        {'document_number': '1', 'full_text_xml_url': 'somewhere'},
        {'document_number': '22', 'full_text_xml_url': 'somewhere'}
    ]))
    path = entry.Entry("path")
    (path / '1_20010101').write(b'v1')
    (path / '1_20020202').write(b'v2')
    (path / '22').write(b'second')
    (path / '22-3344').write(b'unrelated file')
    assert versions.fetch_version_ids('title', 'part', path) == [
        '1_20010101', '1_20020202', '22']


@pytest.mark.django_db
def test_fetch_version_ids_skip_no_xml(monkeypatch):
    """We'll skip over all of the versions which don't have XML"""
    monkeypatch.setattr(versions, 'fetch_notice_json', Mock(return_value=[
        {'document_number': '1', 'full_text_xml_url': 'something'},
        {'document_number': '2', 'full_text_xml_url': None},
        {'document_number': '3', 'full_text_xml_url': 'somewhere'}
    ]))
    path = entry.Entry("path")
    assert ['1', '3'] == versions.fetch_version_ids('title', 'part', path)


def test_delays():
    """For NoticeXMLs which cause delays to other NoticeXMLs, we'd like to get
    a dictionary of delayed -> Delay(delayer, delayed_until)"""
    not_involved, delayed, delayer = Mock(), Mock(), Mock()
    not_involved.configure_mock(
        published=1, fr_volume='vvv', start_page=100, end_page=200,
        version_id='1', **{'delays.return_value': []})
    delayed.configure_mock(
        published=2, fr_volume='vvv', start_page=300, end_page=400,
        version_id='2', **{'delays.return_value': []})
    delayer.configure_mock(
        published=3, fr_volume='vvv', start_page=500, end_page=600,
        version_id='3',
        **{'delays.return_value': [FRDelay('other', 1, 'another-date'),
                                   FRDelay('vvv', 350, 'new-date')]})

    delays = versions.delays([not_involved, delayed, delayer])
    assert delays == {'2': versions.Delay('3', 'new-date')}


def test_delays_order():
    """A NoticeXML's effective date can be delayed by multiple NoticeXMLs.
    Last one wins"""
    delayed, delayer1, delayer2 = Mock(), Mock(), Mock()
    delayed.configure_mock(
        published=1, fr_volume='vvv', start_page=100, end_page=200,
        version_id='1', **{'delays.return_value': []})
    delayer1.configure_mock(
        published=2, fr_volume='vvv', start_page=200, end_page=300,
        version_id='2',
        **{'delays.return_value': [FRDelay('vvv', 100, 'zzz-date')]})
    delayer2.configure_mock(
        published=3, fr_volume='vvv', start_page=300, end_page=400,
        version_id='3',
        **{'delays.return_value': [FRDelay('vvv', 100, 'aaa-date')]})

    delays = versions.delays([delayed, delayer2, delayer1])
    assert delays == {'1': versions.Delay('3', 'aaa-date')}

    delays = versions.delays([delayed, delayer1, delayer2])
    assert delays == {'1': versions.Delay('3', 'aaa-date')}


@pytest.mark.django_db
def test_write_to_disk():
    """If a version has been delayed, its effective date should be part of the
    serialized json"""
    xml = Mock(effective=date(2002, 2, 2), version_id='111',
               fr_citation=Citation(1, 1))
    path = entry.Version('12', '1000')
    versions.write_to_disk(xml, path / '111')

    xml.version_id = '222'
    versions.write_to_disk(
        xml, path / '222',
        versions.Delay(by='333', until=date(2004, 4, 4)))

    assert (path / '111').read().effective == date(2002, 2, 2)
    assert (path / '222').read().effective == date(2004, 4, 4)


@pytest.mark.django_db
def test_write_if_needed_raises_exception(monkeypatch):
    """If an input file is missing, this raises an exception"""
    with pytest.raises(dependency.Missing):
        versions.write_if_needed('title', 'part', ['111'], {'111': 'xml111'},
                                 {})


@pytest.mark.django_db
def test_write_if_needed_output_missing(monkeypatch):
    """If the output file is missing, we'll always write"""
    monkeypatch.setattr(versions, 'write_to_disk', Mock())
    entry.Entry('notice_xml', '111').write(b'content')
    versions.write_if_needed('title', 'part', ['111'], {'111': 'xml111'}, {})
    assert versions.write_to_disk.called


@pytest.mark.django_db
def test_write_if_needed_no_need_to_recompute(monkeypatch):
    """If all dependencies are up to date and the output is present, there's
    no need to write anything"""
    monkeypatch.setattr(versions, 'write_to_disk', Mock())
    entry.Entry('notice_xml', '111').write(b'content')
    entry.Entry('version', 'title', 'part', '111').write(b'out')
    versions.write_if_needed('title', 'part', ['111'], {'111': 'xml111'}, {})
    assert not versions.write_to_disk.called


@pytest.mark.django_db
def test_write_if_needed_delays(monkeypatch):
    """Delays introduce dependencies."""
    monkeypatch.setattr(versions, 'write_to_disk', Mock())
    entry.Entry('notice_xml', '111').write(b'content')
    entry.Entry('notice_xml', '222').write(b'content')
    entry.Entry('version', 'title', 'part', '111').write(b'out')
    versions.write_if_needed(
        'title', 'part', ['111'], {'111': 'xml111'},
        {'111': versions.Delay('222', 'until-date')})
    assert not versions.write_to_disk.called

    # Simulate a change to an input file
    label_id = str(entry.Notice('222'))
    new_time = timezone.now() + timedelta(hours=1)
    DBEntry.objects.filter(label_id=label_id).update(modified=new_time)
    versions.write_if_needed(
        'title', 'part', ['111'], {'111': 'xml111'},
        {'111': versions.Delay('222', 'until-date')})
    assert versions.write_to_disk.called


def test_write_to_disk_no_effective(monkeypatch):
    """If a version is somehow associated with a proposed rule (or a final
    rule has been misparsed), we should get a warning"""
    xml = Mock(effective=None, version_id='vv123')
    monkeypatch.setattr(versions, 'logger', Mock())

    versions.write_to_disk(xml, entry.Version('12', '1000', '11'))

    assert versions.logger.warning.called
    assert 'vv123' in versions.logger.warning.call_args[0]
