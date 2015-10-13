"""The eregs_index directory contains the output for many of the shell
commands. This module provides a quick interface to this index"""
import os

from lxml import etree


ROOT = ".eregs_index"


class Path(object):
    """Encapsulates access to a particular directory within the index"""
    def __init__(self, *dirs):
        self.path = os.path.join(ROOT, *dirs)

    def _create(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def write(self, label, content):
        self._create()
        with open(os.path.join(self.path, label), "w") as f:
            f.write(content)

    def read(self, label):
        self._create()
        with open(os.path.join(self.path, label)) as f:
            return f.read()

    def read_xml(self, label):
        return etree.fromstring(self.read(label))

    def __len__(self):
        self._create()
        return sum(1 for name in os.listdir(self.path)
                   if os.path.isfile(os.path.join(self.path, name)))
