import codecs
import logging
import os
import os.path
import shutil

import requests
from git import Repo
from git.exc import InvalidGitRepositoryError

from regparser.notice.encoder import AmendmentEncoder
from regparser.tree.struct import Node, NodeEncoder

logger = logging.getLogger(__name__)


class AmendmentNodeEncoder(AmendmentEncoder, NodeEncoder):
    pass


class FSWriteContent:
    """This writer places the contents in the file system """

    def __init__(self, *path_parts):
        self.path = os.path.join(*path_parts)

    def write(self, python_obj):
        """Write the object as json to disk"""
        logger.debug("Writing %s", self.path)
        dir_path = os.path.split(self.path)[0]
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(self.path, 'w') as out:
            text = AmendmentNodeEncoder(
                sort_keys=True, indent=4,
                separators=(', ', ': ')).encode(python_obj)
            out.write(text)


class APIWriteContent:
    """This writer writes the contents to the specified API"""
    def __init__(self, *path_parts):
        self.path = "/".join(path_parts)

    def write(self, python_obj):
        """Write the object (as json) to the API"""
        logger.debug("Writing %s", self.path)
        requests.post(
            self.path,
            data=AmendmentNodeEncoder().encode(python_obj),
            headers={'content-type': 'application/json'})


class GitWriteContent:
    """This writer places the content in a git repo on the file system"""
    def __init__(self, *path_parts):
        self.path = os.path.join(*path_parts)

    @staticmethod
    def folder_name(node):
        """Directories are generally just the last element a node's label,
        but subparts and interpretations are a little special."""
        if node.node_type == Node.SUBPART:
            return '-'.join(node.label[-2:])
        elif len(node.label) > 2 and node.label[-1] == Node.INTERP_MARK:
            return '-'.join(node.label[-2:])
        else:
            return node.label[-1]

    def write_tree(self, root_path, node):
        """Given a file system path and a node, write the node's contents and
        recursively write its children to the provided location."""
        if not os.path.exists(root_path):
            os.makedirs(root_path)

        node_text = u"---\n"
        if node.title:
            node_text += 'title: "' + node.title + '"\n'
        node_text += 'node_type: ' + node.node_type + '\n'
        child_folders = [self.folder_name(child) for child in node.children]

        node_text += 'children: ['
        node_text += ', '.join('"' + f + '"' for f in child_folders)
        node_text += ']\n'

        node_text += '---\n' + node.text
        with codecs.open(root_path + os.sep + 'index.md', 'w', 'utf-8') as f:
            f.write(node_text)

        for idx, child in enumerate(node.children):
            child_path = root_path + os.sep + child_folders[idx]
            shutil.rmtree(child_path, ignore_errors=True)
            self.write_tree(child_path, child)

    def write(self, python_object):
        logger.debug("Writing %s", self.path)
        if "regulation" in self.path:
            dir_path, version_id = os.path.split(self.path)
            cfr_part = os.path.split(dir_path)[1]
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            try:
                repo = Repo(dir_path)
            except InvalidGitRepositoryError:
                repo = Repo.init(dir_path)
                repo.index.commit("Initial commit for " + cfr_part)

            # Write all files (and delete any old ones)
            self.write_tree(dir_path, python_object)
            # Add and new files to git
            repo.index.add(repo.untracked_files)
            # Delete and modify files as needed
            deleted, modified = [], []
            for diff in repo.index.diff(None):
                if diff.deleted_file:
                    deleted.append(diff.a_blob.path)
                else:
                    modified.append(diff.a_blob.path)
            if modified:
                repo.index.add(modified)
            if deleted:
                repo.index.remove(deleted)
            # Commit with the notice id as the commit message
            repo.index.commit(version_id)


class Client:
    """A Client for writing regulation(s) and meta data."""

    def __init__(self, base):
        if base.startswith('file://'):
            base = base[len('file://'):]

        if base.startswith('http://') or base.startswith('https://'):
            self.writer_class = APIWriteContent
            self.base = base    # keep the protocol, etc.
        elif base.startswith('git://'):
            self.writer_class = GitWriteContent
            self.base = base[len('git://'):]
        else:
            self.writer_class = FSWriteContent
            self.base = base

    def regulation(self, label, doc_number):
        return self.writer_class(self.base, "regulation", label, doc_number)

    def layer(self, layer_name, doc_type, doc_id):
        return self.writer_class(self.base, "layer", layer_name, doc_type,
                                 doc_id)

    def notice(self, doc_number):
        return self.writer_class(self.base, "notice", doc_number)

    def diff(self, label, old_version, new_version):
        return self.writer_class(self.base, "diff", label, old_version,
                                 new_version)

    def preamble(self, doc_number):
        return self.writer_class(self.base, "preamble", doc_number)
