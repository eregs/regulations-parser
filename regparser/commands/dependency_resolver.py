import abc
import os
import re


class DependencyResolver(object):
    """Base class for objects which know how to "fix" missing dependencies."""
    __metaclass__ = abc.ABCMeta
    # The path of dependencies which this can resolve, split into components
    # which will be combined into a regex
    PATH_PARTS = tuple()

    def __init__(self, dependency_path):
        regex = re.compile(re.escape(os.sep).join(self.PATH_PARTS))
        self.match = regex.match(dependency_path)

    def has_resolution(self):
        return bool(self.match)

    @abc.abstractmethod
    def resolution(self):
        """This will generally call a command in an effort to resolve a
        dependency"""
        raise NotImplementedError()
