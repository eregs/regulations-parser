from datetime import date, timedelta
from unittest import TestCase

from click.testing import CliRunner
from django.utils import timezone
from mock import Mock, patch
import pytest

from regparser.commands import versions
from regparser.history.delays import FRDelay
from regparser.index import dependency, entry
from regparser.web.index.models import Entry as DBEntry


@pytest.mark.django_db
class CommandsVersionsTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    @patch("regparser.commands.versions.fetch_notice_json")
    def test_fetch_version_ids_no_local(self, fetch_notice_json):
        """If there are no local copies, the document numbers found in the FR
        notices should be passed through"""
        fetch_notice_json.return_value = [{'document_number': '1'},
                                          {'document_number': '22'}]
        with self.cli.isolated_filesystem():
            path = entry.Entry("path")
            self.assertEqual(['1', '22'],
                             versions.fetch_version_ids('title', 'part', path))

    @patch("regparser.commands.versions.fetch_notice_json")
    def test_fetch_version_ids_local(self, fetch_notice_json):
        """If a notice is split into multiple entries locally, a single
        document number might result in multiple version ids"""
        fetch_notice_json.return_value = [{'document_number': '1'},
                                          {'document_number': '22'}]
        with self.cli.isolated_filesystem():
            path = entry.Entry("path")
            (path / '1_20010101').write(b'v1')
            (path / '1_20020202').write(b'v2')
            (path / '22').write(b'second')
            (path / '22-3344').write(b'unrelated file')
            self.assertEqual(['1_20010101', '1_20020202', '22'],
                             versions.fetch_version_ids('title', 'part', path))

    def test_delays(self):
        """For NoticeXMLs which cause delays to other NoticeXMLs, we'd like to
        get a dictionary of delayed -> Delay(delayer, delayed_until)"""
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
        self.assertEqual(delays, {'2': versions.Delay('3', 'new-date')})

    def test_delays_order(self):
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
        self.assertEqual(delays, {'1': versions.Delay('3', 'aaa-date')})

        delays = versions.delays([delayed, delayer1, delayer2])
        self.assertEqual(delays, {'1': versions.Delay('3', 'aaa-date')})

    def test_write_to_disk(self):
        """If a version has been delayed, its effective date should be part of
        the serialized json"""
        xml = Mock()
        path = entry.Version('12', '1000')
        with self.cli.isolated_filesystem():
            xml.configure_mock(effective=date(2002, 2, 2), version_id='111',
                               published=date(2002, 1, 1))
            versions.write_to_disk(xml, path / '111')

            xml.configure_mock(version_id='222')
            versions.write_to_disk(
                xml, path / '222',
                versions.Delay(by='333', until=date(2004, 4, 4)))

            self.assertEqual((path / '111').read().effective, date(2002, 2, 2))
            self.assertEqual((path / '222').read().effective, date(2004, 4, 4))

    @patch('regparser.commands.versions.write_to_disk')
    def test_write_if_needed_raises_exception(self, write_to_disk):
        """If an input file is missing, this raises an exception"""
        with self.cli.isolated_filesystem():
            with self.assertRaises(dependency.Missing):
                versions.write_if_needed('title', 'part', ['111'],
                                         {'111': 'xml111'}, {})

    @patch('regparser.commands.versions.write_to_disk')
    def test_write_if_needed_output_missing(self, write_to_disk):
        """If the output file is missing, we'll always write"""
        with self.cli.isolated_filesystem():
            entry.Entry('notice_xml', '111').write(b'content')
            versions.write_if_needed('title', 'part', ['111'],
                                     {'111': 'xml111'}, {})
            self.assertTrue(write_to_disk.called)

    @patch('regparser.commands.versions.write_to_disk')
    def test_write_if_needed_no_need_to_recompute(self, write_to_disk):
        """If all dependencies are up to date and the output is present,
        there's no need to write anything"""
        with self.cli.isolated_filesystem():
            entry.Entry('notice_xml', '111').write(b'content')
            entry.Entry('version', 'title', 'part', '111').write(b'out')
            versions.write_if_needed('title', 'part', ['111'],
                                     {'111': 'xml111'}, {})
            self.assertFalse(write_to_disk.called)

    @patch('regparser.commands.versions.write_to_disk')
    def test_write_if_needed_delays(self, write_to_disk):
        """Delays introduce dependencies."""
        with self.cli.isolated_filesystem():
            entry.Entry('notice_xml', '111').write(b'content')
            entry.Entry('notice_xml', '222').write(b'content')
            entry.Entry('version', 'title', 'part', '111').write(b'out')
            versions.write_if_needed(
                'title', 'part', ['111'], {'111': 'xml111'},
                {'111': versions.Delay('222', 'until-date')})
            self.assertFalse(write_to_disk.called)

            # Simulate a change to an input file
            label_id = str(entry.Notice('222'))
            new_time = timezone.now() + timedelta(hours=1)
            DBEntry.objects.filter(label_id=label_id).update(modified=new_time)
            versions.write_if_needed(
                'title', 'part', ['111'], {'111': 'xml111'},
                {'111': versions.Delay('222', 'until-date')})
            self.assertTrue(write_to_disk.called)


def test_write_to_disk_no_effective(monkeypatch):
    """If a version is somehow associated with a proposed rule (or a final
    rule has been misparsed), we should get a warning"""
    xml = Mock(effective=None, version_id='vv123')
    monkeypatch.setattr(versions, 'logger', Mock())

    versions.write_to_disk(xml, entry.Version('12', '1000', '11'))

    assert versions.logger.warning.called
    assert 'vv123' in versions.logger.warning.call_args[0]
