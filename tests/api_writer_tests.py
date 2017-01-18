import json
import os
import shutil
import tempfile
from unittest import TestCase

from regparser.api_writer import (APIWriteContent, Client, FSWriteContent,
                                  GitWriteContent, Repo)
from regparser.notice.amdparser import Amendment
from regparser.test_utils.http_mixin import HttpMixin
from regparser.tree.struct import Node


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

    def _assert_git_results(self, dir_path, paragraph_label):
        """Validate generated files/directories.
        :param str dir_path: path to the root of the git repo
        :param tuple paragraph_label: an extra directory to check"""
        self.assertTrue(os.path.exists(os.path.join(dir_path, '.git')))
        paths = [
            ('Subpart-E',), ('Subpart-E', '3'), ('Subpart-E', '3', 'a'),
            ('A',), ('A', '3(a)'),
            ('Interp',), ('Interp', '3-Interp'), ('Interp', '3-Interp', '1'),
            ('Interp', '3-Interp', 'a-Interp'),
            ('Interp', '3-Interp', 'a-Interp', '1')] + [paragraph_label]
        dirs, files = [], []
        for dirname, child_dirs, filenames in os.walk(dir_path):
            if ".git" not in dirname:
                dirs.extend(os.path.join(dirname, c) for c in child_dirs
                            if c != '.git')
                files.extend(os.path.join(dirname, f) for f in filenames)
        for path in paths:
            path = os.path.join(dir_path, *path)
            self.assertIn(path, dirs)
            self.assertIn(os.path.join(path, 'index.md'), files)
        return dirs

    def test_write(self):
        """Integration test. @todo: break this up"""
        p3b = Node('(b) Par b', label=['1111', '3', 'b'])
        subpart = Node('', label=['1111', 'Subpart', 'E'], title='Subpart E',
                       node_type=Node.SUBPART, children=[
            Node('Things like: ', label=['1111', '3'], title='Section 3',
                 children=[Node('(a) Par a', label=['1111', '3', 'a']),
                           p3b])])
        appendix = Node(label=['1111', 'A'], title='Appendix A',
                        node_type=Node.APPENDIX, children=[
            Node('Appendix A-3(a)', label=['1111', 'A', '3(a)'],
                 title='A-3(a) - Some Title', node_type=Node.APPENDIX)])
        interp = Node(label=['1111', 'Interp'], node_type=Node.INTERP,
                      title='Supplement I', children=[
            Node(label=['1111', '3', 'Interp'], node_type=Node.INTERP,
                 title='Section 1111.3', children=[
                Node(label=['1111', '3', 'a', 'Interp'],
                     title='Paragraph 3(a)', node_type=Node.INTERP, children=[
                    Node('1. P1', label=['1111', '3', 'a', 'Interp', '1'],
                         node_type=Node.INTERP)]),
                Node('1. Section 3', label=['1111', '3', 'Interp', '1'],
                     node_type=Node.INTERP)])])

        tree = Node('Root text', label=['1111'], title='Regulation Joe',
                    children=[subpart, appendix, interp])
        dir_path = os.path.join(self.tmpdir, "regulation", "1111")

        GitWriteContent(self.tmpdir, "regulation", "1111", "v1v1").write(tree)
        self._assert_git_results(dir_path, ('Subpart-E', '3', 'b'))

        p3c = p3b
        p3c.text = '(c) Moved!'
        p3c.label = ['1111', '3', 'c']

        GitWriteContent(self.tmpdir, "regulation", "1111", "v2v2").write(tree)
        dirs = self._assert_git_results(dir_path, ('Subpart-E', '3', 'c'))
        self.assertNotIn(dir_path + os.path.join('Subpart-E', '3', 'b'), dirs)

        commit = Repo(dir_path).head.commit
        self.assertIn('v2v2', commit.message)
        self.assertEqual(1, len(commit.parents))
        commit = commit.parents[0]
        self.assertIn('v1v1', commit.message)
        self.assertEqual(1, len(commit.parents))
        commit = commit.parents[0]
        self.assertIn('1111', commit.message)
        self.assertEqual(0, len(commit.parents))


def test_regulation(tmpdir):
    reg_writer = Client(str(tmpdir)).regulation("lablab", "docdoc")
    assert reg_writer.path == str(
        tmpdir.join("regulation", "lablab", "docdoc"))


def test_layer(tmpdir):
    reg_writer = Client(str(tmpdir)).layer("boblayer", "lablab", "docdoc")
    assert reg_writer.path == str(
        tmpdir.join("layer", "boblayer", "lablab", "docdoc"))


def test_notice(tmpdir):
    reg_writer = Client(str(tmpdir)).notice("docdoc")
    assert reg_writer.path == str(tmpdir.join("notice", "docdoc"))


def test_diff(tmpdir):
    reg_writer = Client(str(tmpdir)).diff("lablab", "oldold", "newnew")
    assert reg_writer.path == str(
        tmpdir.join("diff", "lablab", "oldold", "newnew"))


def test_preamble(tmpdir):
    reg_writer = Client(str(tmpdir)).preamble("docdoc")
    assert reg_writer.path == str(tmpdir.join("preamble", "docdoc"))


def test_writer_class_fs():
    """File System writer is the appropriate class when a protocol isn't
    present."""
    client = Client('/path/to/somewhere')
    assert client.base == '/path/to/somewhere'
    assert client.writer_class == FSWriteContent

    client = Client('file://somewhere')
    assert client.base == 'somewhere'
    assert client.writer_class == FSWriteContent


def test_writer_class_git():
    """Git will be used if the protocol is git://"""
    client = Client('git://some/path')
    assert client.base == 'some/path'
    assert client.writer_class == GitWriteContent


def test_writer_class_api():
    """Uses APIWriteContent if the base begins with http or https"""
    client = Client('http://example.com/then/more')
    assert client.base == 'http://example.com/then/more'
    assert client.writer_class == APIWriteContent

    client = Client('https://example.com/then/more')
    assert client.base == 'https://example.com/then/more'
    assert client.writer_class == APIWriteContent
