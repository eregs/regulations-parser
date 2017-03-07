from datetime import date

import pytest
from mock import Mock, call

from regparser.commands import versions
from regparser.index import entry
from regparser.notice.xml import NoticeXML
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile


@pytest.mark.django_db
def test_fetch_version_ids_no_local(monkeypatch):
    """If there are no local copies, the document numbers found in the FR
    notices should be passed through"""
    monkeypatch.setattr(versions, 'fetch_notice_json', Mock(return_value=[
        {'document_number': '1', 'full_text_xml_url': 'somewhere'},
        {'document_number': '22', 'full_text_xml_url': 'somewhere'}
    ]))
    assert ['1', '22'] == versions.fetch_version_ids('title', 'part')


@pytest.mark.django_db
def test_fetch_version_ids_local(monkeypatch):
    """If a notice is split into multiple entries locally, a single document
    number might result in multiple version ids"""
    monkeypatch.setattr(versions, 'fetch_notice_json', Mock(return_value=[
        {'document_number': '1', 'full_text_xml_url': 'somewhere'},
        {'document_number': '22', 'full_text_xml_url': 'somewhere'}
    ]))
    path = entry.Entry("notice_xml")
    (path / '1_20010101').write(b'v1')
    (path / '1_20020202').write(b'v2')
    (path / '22').write(b'second')
    (path / '22-3344').write(b'unrelated file')
    assert versions.fetch_version_ids('title', 'part') == [
        '1_20010101', '1_20020202', '22']


@pytest.mark.django_db
def test_fetch_version_ids_skip_no_xml(monkeypatch):
    """We'll skip over all of the versions which don't have XML"""
    monkeypatch.setattr(versions, 'fetch_notice_json', Mock(return_value=[
        {'document_number': '1', 'full_text_xml_url': 'something'},
        {'document_number': '2', 'full_text_xml_url': None},
        {'document_number': '3', 'full_text_xml_url': 'somewhere'}
    ]))
    assert ['1', '3'] == versions.fetch_version_ids('title', 'part')


@pytest.mark.django_db
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
def test_create_version():
    """If a version has been delayed, its effective date should be part of the
    serialized json"""
    notice_xml1 = NoticeXML(b'<ROOT/>')
    notice_xml1.version_id = 'aaa'
    notice_xml1.effective = date(2002, 2, 2)
    notice_xml1.fr_volume = 1
    notice_xml1.start_page = 1
    notice_xml1.save()

    notice_xml2 = NoticeXML(b'<ROOT/>')
    notice_xml2.version_id = 'bbb'
    notice_xml2.save()

    sources = {'aaa': SourceFile.objects.get(file_name='aaa'),
               'bbb': SourceFile.objects.get(file_name='bbb')}

    versions.create_version('12', '1000', sources, 'aaa')
    saved = CFRVersion.objects.get()
    assert saved.effective == date(2002, 2, 2)
    assert saved.source == sources['aaa']
    assert saved.delaying_source is None
    CFRVersion.objects.all().delete()

    versions.create_version('12', '1000', sources, 'aaa',
                            versions.Delay(by='bbb', until=date(2004, 4, 4)))
    saved = CFRVersion.objects.get()
    assert saved.effective == date(2004, 4, 4)
    assert saved.source == sources['aaa']
    assert saved.delaying_source == sources['bbb']


@pytest.mark.django_db
def test_generate_source_calls_preprocessor(monkeypatch):
    """If a SourceFile is missing, we should call the preprocess function"""
    ctx = Mock()

    def create_source(*args, **kwargs):
        SourceFile.objects.create(
            collection=SourceCollection.notice.name, file_name='aaa')

    ctx.invoke.side_effect = create_source
    versions.generate_source('aaa', ctx)
    assert ctx.invoke.call_args == call(versions.preprocess_notice,
                                        document_number='aaa')


@pytest.mark.django_db
def test_create_if_needed_output_missing(monkeypatch):
    """If the output file is missing, we'll always write"""
    monkeypatch.setattr(versions, 'create_version', Mock())
    entry.Entry('notice_xml', 'aaa').write(b'content')
    versions.create_if_needed(111, 22, [SourceFile(file_name='aaa')], {})
    assert versions.create_version.called


@pytest.mark.django_db
def test_generate_source_no_need_to_recompute(monkeypatch):
    """If the SourceFile is present, there's no need to call precompute"""
    sf = SourceFile.objects.create(
        collection=SourceCollection.notice.name, file_name='aaa')
    ctx = Mock()
    assert sf == versions.generate_source('aaa', ctx)
    assert not ctx.invoke.called


@pytest.mark.django_db
def test_create_version_no_effective(monkeypatch):
    """If a version is somehow associated with a proposed rule (or a final
    rule has been misparsed), we should get a warning"""
    notice_xml = NoticeXML(b'<ROOT><DATES/></ROOT>')
    notice_xml.version_id = 'aaa'
    notice_xml.save()

    sources = {'aaa': SourceFile.objects.get(file_name='aaa')}
    monkeypatch.setattr(versions, 'logger', Mock())

    versions.create_version('not', 'used', sources, 'aaa')

    assert versions.logger.warning.called
    assert 'aaa' in versions.logger.warning.call_args[0]
