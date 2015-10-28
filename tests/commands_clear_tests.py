import os
from unittest import TestCase

from click.testing import CliRunner

from regparser import eregs_index
from regparser.commands.clear import clear


class CommandsClearTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_no_errors_when_clear(self):
        """Should raise no errors when no cached files are present"""
        with self.cli.isolated_filesystem():
            self.cli.invoke(clear)

    def test_deletes_fr_cache(self):
        with self.cli.isolated_filesystem():
            open('fr_cache.sqlite', 'w').close()
            self.assertTrue(os.path.exists('fr_cache.sqlite'))

            # flag must be present
            self.cli.invoke(clear)
            self.assertTrue(os.path.exists('fr_cache.sqlite'))

            self.cli.invoke(clear, ['--http-cache'])
            self.assertFalse(os.path.exists('fr_cache.sqlite'))

    def test_deletes_index(self):
        with self.cli.isolated_filesystem():
            eregs_index.Entry('aaa', 'bbb').write('ccc')
            eregs_index.Entry('bbb', 'ccc').write('ddd')
            self.assertEqual(1, len(eregs_index.Entry("aaa")))
            self.assertEqual(1, len(eregs_index.Entry("bbb")))

            self.cli.invoke(clear)
            self.assertEqual(0, len(eregs_index.Entry("aaa")))
            self.assertEqual(0, len(eregs_index.Entry("bbb")))

    def test_deletes_can_be_focused(self):
        """If params are provided to delete certain directories, only those
        directories should get removed"""
        with self.cli.isolated_filesystem():
            to_delete = ['delroot/aaa/bbb', 'delroot/aaa/ccc',
                         'root/delsub/aaa', 'root/delsub/bbb']
            to_keep = ['root/othersub/aaa', 'root/aaa',
                       'top-level-file', 'other-root/aaa']

            for path in to_delete + to_keep:
                eregs_index.Entry(*path.split('/')).write('')

            self.cli.invoke(clear, ['delroot', 'root/delsub'])
            self.assertItemsEqual(['top-level-file', 'root', 'other-root'],
                                  list(eregs_index.Entry()))
            self.assertItemsEqual(['othersub', 'aaa'],
                                  list(eregs_index.Entry('root')))
            self.assertItemsEqual(['aaa'],
                                  list(eregs_index.Entry('other-root')))
