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

            self.cli.invoke(clear)
            self.assertFalse(os.path.exists('fr_cache.sqlite'))

    def test_deletes_index(self):
        with self.cli.isolated_filesystem():
            eregs_index.Path('aaa').write('bbb', 'ccc')
            eregs_index.Path('bbb').write('ccc', 'ddd')
            self.assertEqual(1, len(eregs_index.Path("aaa")))
            self.assertEqual(1, len(eregs_index.Path("bbb")))

            self.cli.invoke(clear)
            self.assertEqual(0, len(eregs_index.Path("aaa")))
            self.assertEqual(0, len(eregs_index.Path("bbb")))
