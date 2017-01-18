import abc
import os
import re

import six
from django.conf import settings


class DependencyResolver(six.with_metaclass(abc.ABCMeta)):
    """Base class for objects which know how to "fix" missing dependencies."""
    # The path of dependencies which this can resolve, split into components
    # which will be combined into a regex
    PATH_PARTS = tuple()

    def __init__(self, dependency_path):
        path_parts = (settings.EREGS_INDEX_ROOT,) + self.PATH_PARTS
        regex = re.compile(re.escape(os.sep).join(path_parts))
        self.match = regex.match(dependency_path)

    def has_resolution(self):
        return bool(self.match)

    @abc.abstractmethod
    def resolution(self):
        """This will generally call a command in an effort to resolve a
        dependency"""
        raise NotImplementedError()
