import calendar
import operator
import string
from datetime import date

import attr
from pyparsing import Optional, Suppress, Word
from six.moves import reduce

from regparser.grammar import utils


@attr.attrs(slots=True, frozen=True)
class EffectiveDate(object):
    """Placeholder token"""


@attr.attrs(slots=True, frozen=True)
class Delayed(object):
    """Placeholder token"""


@attr.attrs(slots=True, frozen=True)
class Notice(object):
    volume = attr.attrib()
    page = attr.attrib()


effective_date = (
    utils.Marker("effective") + utils.Marker("date")
).setParseAction(EffectiveDate)


notice_citation = (
    Word(string.digits) +
    utils.Marker('FR') +
    Word(string.digits)
).setParseAction(lambda m: Notice(int(m[0]), int(m[1])))


delayed = utils.Marker("delayed").setParseAction(Delayed)


def _month_parser(month_idx):
    """Separate function to account for lexical scoping on lambdas"""
    month_name = calendar.month_name[month_idx]
    return utils.Marker(month_name).setParseAction(lambda: month_idx)


months = reduce(operator.ior, (_month_parser(i) for i in range(1, 13)))


date_parser = (
    months +
    Word(string.digits) +
    Suppress(Optional(",")) +
    Word(string.digits)
).setParseAction(lambda m: date(int(m[2]), m[0], int(m[1])))


tokenizer = utils.QuickSearchable(
    effective_date | notice_citation | delayed | date_parser)
