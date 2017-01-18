import json
import os
import shutil
import tempfile
from unittest import TestCase

import click
from click.testing import CliRunner
from mock import patch

from regparser.commands import compare_to
from regparser.test_utils.http_mixin import HttpMixin


class CommandsCompareToTests(HttpMixin, TestCase):
    def setUp(self):
        super(CommandsCompareToTests, self).setUp()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        super(CommandsCompareToTests, self).tearDown()

    def populate(self, files):
        """Create the requested files in the tempdir. The files param should
        be a list of tuples, denoting file path components"""
        for file_parts in files:
            dir_name = os.path.join(self.tmpdir, *file_parts[:-1])
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            with open(os.path.join(dir_name, file_parts[-1]), 'w') as f:
                f.write('content')
        return [os.path.join(*parts) for parts in files]

    def test_local_and_remote_generator(self):
        """Files to compare should find all of the files present in the temp
        directory"""
        root = os.path.join(self.tmpdir, 'diff')
        os.makedirs(os.path.join(root, 'dir1', 'sub1'))
        os.makedirs(os.path.join(root, 'dir1', 'sub2'))
        os.makedirs(os.path.join(root, 'dir2'))
        for parts in (('dir1', 'sub1', 'a'), ('dir1', 'sub1', 'b'),
                      ('dir1', 'sub2', 'c'),
                      ('dir2', 'd'), ('dir2', 'e'),
                      ('f',)):
            with open(os.path.join(root, *parts), 'w') as f:
                f.write('content')

        gen = compare_to.local_and_remote_generator
        self.assertEqual(2, len(list(gen('', [os.path.join(root, 'dir2')]))))
        self.assertEqual(
            4, len(list(gen('', [os.path.join(root, 'dir1', 'sub1'),
                                 os.path.join(root, 'dir2')]))))
        self.assertEqual(1, len(list(gen('', [os.path.join(root, 'f')]))))
        self.assertEqual(6, len(list(gen('', [root]))))

    def run_compare(self, local_path, remote_url, input_val=None):
        """Our CLI library, Click, is easier to test via click.commands. So we
        create one to wrap compare_to.compare, run it, and return the
        results"""

        @click.command()
        def wrapper():
            compare_to.compare(local_path, remote_url)

        return CliRunner().invoke(wrapper, input=input_val)

    def test_compare_404(self):
        """If the remote file doesn't exist, we should be notified"""
        self.expect_json_http(status=404)
        with patch('regparser.commands.compare_to.logger') as logger:
            self.run_compare('local_file', 'http://example.com/remote')
        self.assertEqual(logger.warning.call_args[0],
                         ('Nonexistent: %s', 'http://example.com/remote'))

    def test_compare_no_diff(self):
        """We shouldn't get any notification if the files are the same"""
        data = {'key1': 1, 'key2': 'a', 'key3': [1, 2, 3]}
        local_path = os.path.join(self.tmpdir, 'file.json')
        with open(local_path, 'w') as f:
            json.dump(data, f)
        self.expect_json_http(data)
        result = self.run_compare(local_path, 'http://example.com/file.json')
        self.assertEqual('', result.output)

    def test_compare_with_diff(self):
        """If the files differ, we should get prompted to see the diff. If we
        say yes, we should see a diff"""
        local_path = os.path.join(self.tmpdir, 'file.json')
        with open(local_path, 'w') as f:
            json.dump({'key1': 1, 'key2': 'b'}, f)
        self.expect_json_http({'key1': 1, 'key2': 'a'})

        # No, I do not want to see diffs
        result = self.run_compare(local_path, 'http://example.com/file.json',
                                  input_val="n\n")
        self.assertTrue('Content differs' in result.output)
        self.assertFalse('key' in result.output)

        # Yes, I do want to see the diffs
        result = self.run_compare(local_path, 'http://example.com/file.json',
                                  input_val="Y\n")
        self.assertTrue('Content differs' in result.output)
        self.assertTrue('-  "a"' in result.output)
        self.assertTrue('+  "b"' in result.output)
