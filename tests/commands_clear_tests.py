import os
from unittest import TestCase

from click.testing import CliRunner
import six

from regparser import index
from regparser.commands.clear import clear
from regparser.index import entry, http_cache


class CommandsClearTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_no_errors_when_clear(self):
        """Should raise no errors when no cached files are present"""
        with self.cli.isolated_filesystem():
            self.cli.invoke(clear)

    def test_deletes_http_cache(self):
        with self.cli.isolated_filesystem():
            os.makedirs(index.ROOT)
            open(http_cache.PATH, 'w').close()
            self.assertTrue(os.path.exists(http_cache.PATH))

            self.cli.invoke(clear)
            self.assertFalse(os.path.exists(http_cache.PATH))

    def test_deletes_index(self):
        with self.cli.isolated_filesystem():
            entry.Entry('aaa', 'bbb').write(b'ccc')
            entry.Entry('bbb', 'ccc').write(b'ddd')
            self.assertEqual(1, len(entry.Entry("aaa")))
            self.assertEqual(1, len(entry.Entry("bbb")))

            self.cli.invoke(clear)
            self.assertEqual(0, len(entry.Entry("aaa")))
            self.assertEqual(0, len(entry.Entry("bbb")))

    def test_deletes_can_be_focused(self):
        """If params are provided to delete certain directories, only those
        directories should get removed"""
        with self.cli.isolated_filesystem():
            to_delete = ['delroot/aaa/bbb', 'delroot/aaa/ccc',
                         'root/delsub/aaa', 'root/delsub/bbb']
            to_keep = ['root/othersub/aaa', 'root/aaa',
                       'top-level-file', 'other-root/aaa']

            for path in to_delete + to_keep:
                entry.Entry(*path.split('/')).write(b'')

            self.cli.invoke(clear, ['delroot', 'root/delsub'])
            six.assertCountEqual(self,
                                 ['top-level-file', 'root', 'other-root'],
                                 list(entry.Entry()))
            six.assertCountEqual(self,
                                 ['othersub', 'aaa'],
                                 list(entry.Entry('root')))
            six.assertCountEqual(self,
                                 ['aaa'],
                                 list(entry.Entry('other-root')))
