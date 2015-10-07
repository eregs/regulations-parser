from datetime import datetime
import re

from lxml import etree

from regparser.tree.xml_parser.tree_utils import get_node_text


def parse_date_sentence(sentence):
    """Return the date type + date in this sentence (if one exists)."""
    #   Search for month date, year at the end of the sentence
    sentence = sentence.lower().strip()
    date_re = r".*((january|february|march|april|may|june|july|august"
    date_re += r"|september|october|november|december) \d+, \d+)$"
    match = re.match(date_re, sentence)
    if match:
        date = datetime.strptime(match.group(1), "%B %d, %Y")
        if 'comment' in sentence:
            return ('comments', date.strftime("%Y-%m-%d"))
        if 'effective' in sentence:
            return ('effective', date.strftime("%Y-%m-%d"))
        return ('other', date.strftime('%Y-%m-%d'))


def fetch_dates(xml):
    """Pull out any dates (and their types) from the XML. Not all notices
    have all types of dates, some notices have multiple dates of the same
    type."""
    dates_field = xml.xpath('//EFFDATE/P') or xml.xpath('//DATES/P')
    dates = {}
    for par in dates_field:
        for sentence in get_node_text(par).split('.'):
            result_pair = parse_date_sentence(sentence.replace('\n', ' '))
            if result_pair:
                date_type, date = result_pair
                dates[date_type] = dates.get(date_type, []) + [date]
    if dates:
        return dates


def set_effective_date(xml, date_str=None):
    """Modify the XML tree so that it contains an explicit effective date.
    Uses the `date_str` if provided; if not, attempts to derive it from the
    DATES tags"""
    if date_str is None:
        dates = fetch_dates(xml) or {}
        if 'effective' not in dates:
            raise Exception("Could not derive effective date for notice")
        date_str = dates['effective'][0]

    effdate = xml.xpath('//EFFDATE')
    if effdate:
        effdate = effdate[0]
    else:     # Tag wasn't present; create it
        effdate = etree.Element("EFFDATE")
        xml.insert(0, effdate)
    effdate.attrib["eregs-effective-date"] = date_str
    return date_str
