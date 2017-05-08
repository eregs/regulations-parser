"""Parsers for various types of external citations. Consumed by the external
citation layer"""
import abc
import re
import string
from collections import namedtuple

import six
from pyparsing import Optional, Suppress, Word
from six.moves.urllib.parse import urlencode

from regparser.citations import cfr_citations
from regparser.grammar.utils import Marker, QuickSearchable
from regparser.web.settings import parser as settings

Cite = namedtuple('Cite', ['cite_type', 'start', 'end', 'components', 'url'])


class FinderBase(six.with_metaclass(abc.ABCMeta)):
    """Base class for all of the external citation parsers. Defines the
    interface they must implement."""
    @abc.abstractproperty
    def CITE_TYPE(self):    # noqa - this is a property
        """A constant to represent the citations this produces."""
        raise NotImplementedError()

    @abc.abstractmethod
    def find(self, node):
        """Give a Node, pull out any external citations it may contain as a
        generator of Cites"""
        raise NotImplementedError()


def fdsys_url(**params):
    """Generate a URL to an FDSYS redirect"""
    params['year'] = params.get('year', 'mostrecent')
    params = sorted(params.items())     # consistent encoding
    return 'http://api.fdsys.gov/link?{0}'.format(urlencode(params))


class CFRFinder(FinderBase):
    """Code of Federal Regulations. Explicitly ignore any references within
    this part"""
    CITE_TYPE = 'CFR'

    def find(self, node):
        for cit in cfr_citations(node.text):
            if cit.label.settings['part'] != node.label[0]:
                fdsys_params = {'titlenum': cit.label.settings['cfr_title'],
                                'partnum': cit.label.settings['part']}
                if 'section' in cit.label.settings:
                    fdsys_params['section'] = cit.label.settings['section']

                yield Cite(self.CITE_TYPE, cit.start, cit.end,
                           cit.label.settings,
                           fdsys_url(collection='cfr', **fdsys_params))


class FDSYSFinder(six.with_metaclass(abc.ABCMeta)):
    """Common parent class to Finders which generate an FDSYS url based on
    matching a PyParsing grammar"""
    @abc.abstractproperty
    def GRAMMAR(self):  # noqa - this is a property
        """A pyparsing grammar with relevant components labeled"""
        raise NotImplementedError()

    @abc.abstractproperty
    def CONST_PARAMS(self):     # noqa - this is a property
        """Constant parameters we pass to the FDSYS url; a dict"""
        raise NotImplementedError()

    def find(self, node):
        for match, start, end in self.GRAMMAR.scanString(node.text):
            params = dict(match)
            params.update(self.CONST_PARAMS)
            yield Cite(self.CITE_TYPE, start, end, dict(match),
                       fdsys_url(**params))


class USCFinder(FDSYSFinder, FinderBase):
    """U.S. Code"""
    CITE_TYPE = 'USC'
    GRAMMAR = QuickSearchable(
        Word(string.digits).setResultsName("title") +
        "U.S.C." +
        Suppress(Optional("Chapter")) +
        Word(string.digits).setResultsName("section"))
    CONST_PARAMS = dict(collection='uscode')


class PublicLawFinder(FDSYSFinder, FinderBase):
    """Public Law"""
    CITE_TYPE = 'PUBLIC_LAW'
    GRAMMAR = QuickSearchable(
        Marker("Public") + Marker("Law") +
        Word(string.digits).setResultsName("congress") + Suppress("-") +
        Word(string.digits).setResultsName("lawnum"))
    CONST_PARAMS = dict(collection='plaw', lawtype='public')


class StatutesFinder(FDSYSFinder, FinderBase):
    """Statutes at large"""
    CITE_TYPE = 'STATUTES_AT_LARGE'
    GRAMMAR = QuickSearchable(
        Word(string.digits).setResultsName("volume") + Suppress("Stat.") +
        Word(string.digits).setResultsName("page"))
    CONST_PARAMS = dict(collection='statute')


class CustomFinder(FinderBase):
    """Explicitly configured citations; part of settings"""
    CITE_TYPE = 'OTHER'
    _cached_regexes = {}

    def find(self, node):
        for needle, url in settings.CUSTOM_CITATIONS.items():
            if needle not in self._cached_regexes:
                self._cached_regexes[needle] = re.compile(
                    r'\b' + re.escape(needle) + r'\b')

            for match in self._cached_regexes[needle].finditer(node.text):
                yield Cite(self.CITE_TYPE, match.start(), match.end(), {},
                           url)


class UrlFinder(FinderBase):
    """Any raw urls in the text"""
    CITE_TYPE = 'OTHER'
    REGEX = re.compile(r'https?:\/\/\S+')
    PUNCTUATION = """.,;?'")-"""

    def find(self, node):
        for match in self.REGEX.finditer(node.text):
            # remove any trailing punctuation
            url = match.group(0).rstrip(self.PUNCTUATION)
            yield Cite(self.CITE_TYPE, match.start(), match.start() + len(url),
                       {}, url)


# Surface all of the external citation finder classes
ALL = FinderBase.__subclasses__()
