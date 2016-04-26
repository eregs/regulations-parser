import json
import os
import shutil
import tempfile
from unittest import TestCase

from regparser.api_writer import (
    APIWriteContent, Client, FSWriteContent, GitWriteContent, Repo)
from regparser.notice.amdparser import Amendment
from regparser.test_utils.http_mixin import HttpMixin
from regparser.tree.struct import Node
import settings


class FSWriteContentTest(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def read(self, *path_parts):
        """Read the requested file, as JSON"""
        with open(os.path.join(self.tmpdir, *path_parts)) as f:
            return json.load(f)

    def test_write_new_dir(self):
        writer = FSWriteContent(self.tmpdir, "a", "path", "to", "something")
        writer.write({"testing": ["body", 1, 2]})

        self.assertEqual(self.read("a", "path", "to", "something"),
                         {'testing': ['body', 1, 2]})

    def test_write_existing_dir(self):
        os.mkdir(os.path.join(self.tmpdir, "existing"))
        writer = FSWriteContent(self.tmpdir, "existing", "thing")
        writer.write({"testing": ["body", 1, 2]})

        self.assertEqual(self.read("existing", "thing"),
                         {'testing': ['body', 1, 2]})

    def test_write_overwrite(self):
        writer = FSWriteContent(self.tmpdir, "replace", "it")
        writer.write({"testing": ["body", 1, 2]})

        writer = FSWriteContent(self.tmpdir, "replace", "it")
        writer.write({"key": "value"})

        self.assertEqual(self.read("replace", "it"), {'key': 'value'})

    def test_write_encoding(self):
        writer = FSWriteContent(self.tmpdir, "replace", "it")
        writer.write(Node("Content"))

        self.assertEqual(self.read("replace", "it")['text'], 'Content')

        writer.write(Amendment("action", "label"))
        self.assertEqual(self.read("replace", "it"), ['action', ['label']])

        writer.write(Amendment("action", "label", 'destination'))
        self.assertEqual(self.read("replace", "it"),
                         ['action', ['label'], ['destination']])


class APIWriteContentTest(HttpMixin, TestCase):
    def test_write(self):
        writer = APIWriteContent("http://example.com", "a", "path")
        data = {"testing": ["body", 1, 2]}
        self.expect_json_http(method='POST', uri='http://example.com/a/path')
        writer.write(data)

        self.assertEqual(self.last_http_headers()['content-type'],
                         'application/json')
        self.assertEqual(self.last_http_body(), data)


class GitWriteContentTest(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_write(self):
        """Integration test. @todo: break this up"""
        p3a = Node('(a) Par a', label=['1111', '3', 'a'])
        p3b = Node('(b) Par b', label=['1111', '3', 'b'])
        p3 = Node('Things like: ', label=['1111', '3'], title='Section 3',
                  children=[p3a, p3b])
        sub = Node('', label=['1111', 'Subpart', 'E'], title='Subpart E',
                   node_type=Node.SUBPART, children=[p3])
        a3a = Node('Appendix A-3(a)', label=['1111', 'A', '3(a)'],
                   title='A-3(a) - Some Title', node_type=Node.APPENDIX)
        app = Node('', label=['1111', 'A'], title='Appendix A',
                   node_type=Node.APPENDIX, children=[a3a])
        i3a1 = Node('1. P1', label=['1111', '3', 'a', 'Interp', '1'],
                    node_type=Node.INTERP)
        i3a = Node('', label=['1111', '3', 'a', 'Interp'],
                   node_type=Node.INTERP, children=[i3a1],
                   title='Paragraph 3(a)')
        i31 = Node('1. Section 3', label=['1111', '3', 'Interp', '1'],
                   node_type=Node.INTERP)
        i3 = Node('', label=['1111', '3', 'Interp'], node_type=Node.INTERP,
                  title='Section 1111.3', children=[i3a, i31])
        i = Node('', label=['1111', 'Interp'], node_type=Node.INTERP,
                 title='Supplement I', children=[i3])
        tree = Node('Root text', label=['1111'], title='Regulation Joe',
                    children=[sub, app, i])

        writer = GitWriteContent(self.tmpdir, "regulation", "1111", "v1v1")
        writer.write(tree)

        dir_path = os.path.join(self.tmpdir, "regulation", "1111")

        self.assertTrue(os.path.exists(os.path.join(dir_path, '.git')))
        dirs, files = [], []
        for dirname, child_dirs, filenames in os.walk(dir_path):
            if ".git" not in dirname:
                dirs.extend(os.path.join(dirname, c) for c in child_dirs
                            if c != '.git')
                files.extend(os.path.join(dirname, f) for f in filenames)
        for path in (('Subpart-E',), ('Subpart-E', '3'),
                     ('Subpart-E', '3', 'a'), ('Subpart-E', '3', 'b'),
                     ('A',), ('A', '3(a)'),
                     ('Interp',), ('Interp', '3-Interp'),
                     ('Interp', '3-Interp', '1'),
                     ('Interp', '3-Interp', 'a-Interp'),
                     ('Interp', '3-Interp', 'a-Interp', '1')):
            path = os.path.join(dir_path, *path)
            self.assertTrue(path in dirs)
            self.assertTrue(path + os.path.sep + 'index.md' in files)

        p3c = p3b
        p3c.text = '(c) Moved!'
        p3c.label = ['1111', '3', 'c']

        writer = GitWriteContent(self.tmpdir, "regulation", "1111", "v2v2")
        writer.write(tree)

        dir_path = os.path.join(self.tmpdir, "regulation", "1111")

        self.assertTrue(os.path.exists(os.path.join(dir_path, '.git')))
        dirs, files = [], []
        for dirname, child_dirs, filenames in os.walk(dir_path):
            if ".git" not in dirname:
                dirs.extend(os.path.join(dirname, c) for c in child_dirs
                            if c != '.git')
                files.extend(os.path.join(dirname, f) for f in filenames)
        for path in (('Subpart-E',), ('Subpart-E', '3'),
                     ('Subpart-E', '3', 'a'), ('Subpart-E', '3', 'c'),
                     ('A',), ('A', '3(a)'),
                     ('Interp',), ('Interp', '3-Interp'),
                     ('Interp', '3-Interp', '1'),
                     ('Interp', '3-Interp', 'a-Interp'),
                     ('Interp', '3-Interp', 'a-Interp', '1')):
            path = os.path.join(dir_path, *path)
            self.assertTrue(path in dirs)
            self.assertTrue(path + os.path.sep + 'index.md' in files)
        self.assertFalse(dir_path + os.path.join('Subpart-E', '3', 'b')
                         in dirs)

        commit = Repo(dir_path).head.commit
        self.assertTrue('v2v2' in commit.message)
        self.assertEqual(1, len(commit.parents))
        commit = commit.parents[0]
        self.assertTrue('v1v1' in commit.message)
        self.assertEqual(1, len(commit.parents))
        commit = commit.parents[0]
        self.assertTrue('1111' in commit.message)
        self.assertEqual(0, len(commit.parents))


class ClientTest(TestCase):
    def setUp(self):
        self.base = settings.API_BASE
        settings.API_BASE = ''

        self.had_git_output = hasattr(settings, 'GIT_OUTPUT_DIR')
        self.old_git_output = getattr(settings, 'GIT_OUTPUT_DIR', '')
        settings.GIT_OUTPUT_DIR = ''

        self.old_output = settings.OUTPUT_DIR
        self.tmpdir = tempfile.mkdtemp()
        settings.OUTPUT_DIR = self.tmpdir

    def tearDown(self):
        settings.API_BASE = self.base
        if self.had_git_output:
            settings.GIT_OUTPUT_DIR = self.old_git_output
        else:
            del(settings.GIT_OUTPUT_DIR)
        shutil.rmtree(self.tmpdir)
        settings.OUTPUT_DIR = self.old_output

    def test_regulation(self):
        reg_writer = Client().regulation("lablab", "docdoc")
        self.assertEqual(
            os.path.join(self.tmpdir, "regulation", "lablab", "docdoc"),
            reg_writer.path)

    def test_layer(self):
        reg_writer = Client().layer("boblayer", "lablab", "docdoc")
        self.assertEqual(
            os.path.join(self.tmpdir, "layer", "boblayer", "lablab", "docdoc"),
            reg_writer.path)

    def test_notice(self):
        reg_writer = Client().notice("docdoc")
        self.assertEqual(
            os.path.join(self.tmpdir, "notice", "docdoc"), reg_writer.path)

    def test_diff(self):
        reg_writer = Client().diff("lablab", "oldold", "newnew")
        self.assertEqual(
            os.path.join(self.tmpdir, "diff", "lablab", "oldold", "newnew"),
            reg_writer.path)

    def test_preamble(self):
        reg_writer = Client().preamble("docdoc")
        self.assertEqual(
            os.path.join(self.tmpdir, "preamble", "docdoc"), reg_writer.path)

    def test_writer_class_fs(self):
        """File System writer is the appropriate class when a protocol isn't
        present. It is also the default"""
        client = Client('/path/to/somewhere')
        self.assertEqual('/path/to/somewhere', client.base)
        self.assertEqual(FSWriteContent, client.writer_class)

        client = Client('file://somewhere')
        self.assertEqual('somewhere', client.base)
        self.assertEqual(FSWriteContent, client.writer_class)

        client = Client()
        self.assertEqual(self.tmpdir, client.base)
        self.assertEqual(FSWriteContent, client.writer_class)

    def test_writer_class_git(self):
        """Git will be used if the protocol is git:// or if GIT_OUTPUT_DIR is
        defined"""
        client = Client('git://some/path')
        self.assertEqual('some/path', client.base)
        self.assertEqual(GitWriteContent, client.writer_class)

        settings.GIT_OUTPUT_DIR = 'another/path'
        client = Client()
        self.assertEqual('another/path', client.base)
        self.assertEqual(GitWriteContent, client.writer_class)

    def test_writer_class_api(self):
        """Uses APIWriteContent if the base begins with http, https, or
        API_BASE is set"""
        client = Client('http://example.com/then/more')
        self.assertEqual('http://example.com/then/more', client.base)
        self.assertEqual(APIWriteContent, client.writer_class)

        client = Client('https://example.com/then/more')
        self.assertEqual('https://example.com/then/more', client.base)
        self.assertEqual(APIWriteContent, client.writer_class)

        settings.API_BASE = 'http://example.com/'
        client = Client()
        self.assertEqual('http://example.com/', client.base)
        self.assertEqual(APIWriteContent, client.writer_class)
