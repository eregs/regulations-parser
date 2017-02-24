from datetime import date, timedelta

import pytest
from django.utils import timezone
from mock import Mock

from regparser.commands import versions
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.web.index.models import Entry as DBEntry
from regparser.web.index.models import CFRVersion, SourceFile


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
    not_involved = NoticeXML(b'<ROOT/>')
    not_involved.version_id = '1'
    not_involved.fr_volume = 1
    not_involved.start_page = 100
    not_involved.end_page = 111
    not_involved.save()

    delayed = NoticeXML(b'<ROOT/>')
    delayed.version_id = '2'
    delayed.fr_volume = 2
    delayed.start_page = 200
    delayed.end_page = 222
    delayed.save()

    delayer = NoticeXML(b"""<ROOT>
        <DATES>
            <P>The effective date of 2 FR 200 has been delayed until January
            1, 2001.</P>
            <P>The effective date of 4 FR 400 has been delayed until February
            2, 2002.</P>
        </DATES>
    </ROOT>""")
    delayer.version_id = '3'
    delayer.fr_volume = 3
    delayer.start_page = 300
    delayer.end_page = 333
    delayer.save()

    delays = versions.delays([
        SourceFile.objects.get(file_name=str(i)) for i in range(1, 4)
    ])
    assert delays == {'2': versions.Delay('3', date(2001, 1, 1))}


@pytest.mark.django_db
def test_delays_order():
    """A NoticeXML's effective date can be delayed by multiple NoticeXMLs.
    Last one wins"""
    delayed = NoticeXML(b'<ROOT/>')
    delayed.version_id = '1'
    delayed.fr_volume = 1
    delayed.start_page = 100
    delayed.end_page = 111
    delayed.save()

    delayer1 = NoticeXML(b"""<ROOT>
        <DATES>
            <P>The effective date of 1 FR 100 has been delayed until January
            1, 2001.</P>
        </DATES>
    </ROOT>""")
    delayer1.version_id = '2'
    delayer1.fr_volume = 2
    delayer1.start_page = 200
    delayer1.end_page = 222
    delayer1.save()

    delayer2 = NoticeXML(b"""<ROOT>
        <DATES>
            <P>The effective date of 1 FR 100 has been delayed until February
            2, 2002.</P>
        </DATES>
    </ROOT>""")
    delayer2.version_id = '3'
    delayer2.fr_volume = 3
    delayer2.start_page = 300
    delayer2.end_page = 333
    delayer2.save()

    sources = [SourceFile.objects.get(file_name=str(i)) for i in range(1, 4)]
    delays = versions.delays([sources[0], sources[2], sources[1]])
    assert delays == {'1': versions.Delay('3', date(2002, 2, 2))}

    delays = versions.delays(sources)
    assert delays == {'1': versions.Delay('3', date(2002, 2, 2))}


@pytest.mark.django_db
def test_write_to_disk():
    """If a version has been delayed, its effective date should be part of the
    serialized json"""
    notice_xml1 = NoticeXML(b'<ROOT/>')
    notice_xml1.version_id = '111'
    notice_xml1.effective = date(2002, 2, 2)
    notice_xml1.fr_volume = 1
    notice_xml1.start_page = 1
    notice_xml1.save()

    notice_xml2 = NoticeXML(b'<ROOT/>')
    notice_xml2.version_id = '222'
    notice_xml2.save()

    sources = {'111': SourceFile.objects.get(file_name='111'),
               '222': SourceFile.objects.get(file_name='222')}

    versions.write_to_disk('12', '1000', sources, '111')
    saved = CFRVersion.objects.get()
    assert saved.effective == date(2002, 2, 2)
    assert saved.source == sources['111']
    assert saved.delaying_source is None

    versions.write_to_disk('12', '1000', sources, '111',
                           versions.Delay(by='222', until=date(2004, 4, 4)))
    saved = CFRVersion.objects.get()
    assert saved.effective == date(2004, 4, 4)
    assert saved.source == sources['111']
    assert saved.delaying_source == sources['222']


@pytest.mark.django_db
def test_write_if_needed_raises_exception(monkeypatch):
    """If an input file is missing, this raises an exception"""
    with pytest.raises(dependency.Missing):
        versions.write_if_needed(
            'title', 'part', [SourceFile(file_name='111')], {})


@pytest.mark.django_db
def test_write_if_needed_output_missing(monkeypatch):
    """If the output file is missing, we'll always write"""
    monkeypatch.setattr(versions, 'write_to_disk', Mock())
    entry.Entry('notice_xml', '111').write(b'content')
    versions.write_if_needed(
        'title', 'part', [SourceFile(file_name='111')], {})
    assert versions.write_to_disk.called


@pytest.mark.django_db
def test_write_if_needed_no_need_to_recompute(monkeypatch):
    """If all dependencies are up to date and the output is present, there's
    no need to write anything"""
    monkeypatch.setattr(versions, 'write_to_disk', Mock())
    entry.Entry('notice_xml', '111').write(b'content')
    entry.Entry('version', 'title', 'part', '111').write(b'out')
    versions.write_if_needed(
        'title', 'part', [SourceFile(file_name='111')], {})
    assert not versions.write_to_disk.called


@pytest.mark.django_db
def test_write_if_needed_delays(monkeypatch):
    """Delays introduce dependencies."""
    monkeypatch.setattr(versions, 'write_to_disk', Mock())
    entry.Entry('notice_xml', '111').write(b'content')
    entry.Entry('notice_xml', '222').write(b'content')
    entry.Entry('version', 'title', 'part', '111').write(b'out')
    entry.Entry('version', 'title', 'part', '222').write(b'out')
    sources = [SourceFile(file_name='111'), SourceFile(file_name='222')]
    delays = {'111': versions.Delay('222', 'until-date')}
    versions.write_if_needed('title', 'part', sources, delays)
    assert not versions.write_to_disk.called

    # Simulate a change to an input file
    label_id = str(entry.Notice('222'))
    new_time = timezone.now() + timedelta(hours=1)
    DBEntry.objects.filter(label_id=label_id).update(modified=new_time)
    versions.write_if_needed('title', 'part', sources, delays)
    assert versions.write_to_disk.called


@pytest.mark.django_db
def test_write_to_disk_no_effective(monkeypatch):
    """If a version is somehow associated with a proposed rule (or a final
    rule has been misparsed), we should get a warning"""
    notice_xml = NoticeXML(b'<ROOT><DATES/></ROOT>')
    notice_xml.version_id = '111'
    notice_xml.save()

    sources = {'111': SourceFile.objects.get(file_name='111')}
    monkeypatch.setattr(versions, 'logger', Mock())

    versions.write_to_disk('not', 'used', sources, '111')

    assert versions.logger.warning.called
    assert '111' in versions.logger.warning.call_args[0]
