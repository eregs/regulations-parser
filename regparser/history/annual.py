# -*- coding: utf-8 -*-
import logging
import os
import re
from collections import namedtuple
from datetime import date

import requests
from cached_property import cached_property

from regparser.index.http_cache import http_client
from regparser.tree.xml_parser.xml_wrapper import XMLWrapper
from regparser.web.settings import parser as settings

CFR_BULK_URL = ("https://www.gpo.gov/fdsys/bulkdata/CFR/{year}/title-{title}/"
                "CFR-{year}-title{title}-vol{volume}.xml")
CFR_PART_URL = ("https://www.gpo.gov/fdsys/pkg/"
                "CFR-{year}-title{title}-vol{volume}/xml/"
                "CFR-{year}-title{title}-vol{volume}-part{part}.xml")

# Matches any of the following:
#    Parts 200 to 219
#    Parts 200 to end
#    Part 52 (§§ 52.1019 to 52.2019)
# Note: The outer parentheses seem to be required by Python, although they
#       shouldn't be
PART_SPAN_REGEX = re.compile(
    r'.*parts? ('
    r'(?P<span>(?P<start>\d+) to ((?P<end>\d+)|(?P<end_literal>end)))'
    r'|((?P<single_part>\d+) \(.*\))'
    r'.*)',
    flags=re.IGNORECASE)
logger = logging.getLogger(__name__)


class Volume(namedtuple('Volume', ['year', 'title', 'vol_num'])):
    @property
    def url(self):
        return CFR_BULK_URL.format(year=self.year, title=self.title,
                                   volume=self.vol_num)

    @cached_property
    def response(self):
        logger.debug("GET %s", self.url)
        return http_client().get(self.url, stream=True)

    @property
    def exists(self):
        return self.response.status_code == 200

    @cached_property
    def part_span(self):
        """Calculate and memoize the range of parts this volume covers"""
        _part_span = False
        part_string = ''

        for line in self.response.iter_lines(decode_unicode=True):
            if '<PARTS>' in line:
                part_string = line
                break
        if part_string:
            match = PART_SPAN_REGEX.match(part_string)
            if match and match.group('span'):
                start = int(match.group('start'))
                if match.group('end_literal'):
                    end = None
                else:
                    end = int(match.group('end'))
                _part_span = (start, end)
            elif match:
                start = int(match.group('single_part'))
                _part_span = (start, start)
            else:
                logger.warning("Can't parse: %s", part_string)
        else:
            logger.warning('No <PARTS> in %s. Assuming this volume '
                           'contains all of the regs', self.url)
            _part_span = (1, None)
        return _part_span

    @property
    def publication_date(self):
        return date(self.year, publication_month(self.title), 1)

    def should_contain(self, part):
        """Does this volume contain the part number requested?"""
        if self.part_span:
            (start, end) = self.part_span
            if start > part:
                return False
            elif end is None:
                return True
            else:
                return end >= part
        else:
            return False

    def find_part_xml(self, part):
        """Pull the XML for an annual edition, first checking locally"""
        logger.info("Find Part xml for %s CFR %s", self.title, part)
        url = CFR_PART_URL.format(year=self.year, title=self.title,
                                  volume=self.vol_num, part=part)
        filename = url.split('/')[-1]
        for xml_path in settings.LOCAL_XML_PATHS:
            xml_path = os.path.join(xml_path, 'annual', filename)
            logger.debug("Checking locally for file %s", xml_path)
            if os.path.isfile(xml_path):
                with open(xml_path, 'rb') as f:
                    return XMLWrapper(f.read(), xml_path)

        client = http_client()
        first_try_url = settings.XML_REPO_PREFIX + 'annual/' + filename
        logging.info('trying to fetch annual edition from %s', first_try_url)
        response = client.get(first_try_url)
        if response.status_code != requests.codes.ok:
            logger.info('failed. fetching from %s', url)
            response = client.get(url)
        if response.status_code == requests.codes.ok:
            return XMLWrapper(response.content, url)


def publication_month(cfr_title):
    """Annual editions are published for different titles at different points
    throughout the year. Return the month associated with this CFR title"""
    if cfr_title <= 16:
        return 1
    elif cfr_title <= 27:
        return 4
    elif cfr_title <= 41:
        return 7
    else:
        return 10


def date_of_annual_after(title, eff_date):
    """Return the date of the _first_ annual edition which should contain any
    changes on `eff_date`. This date may well be in the future"""
    publication_date = date(eff_date.year, publication_month(title), 1)
    if eff_date <= publication_date:
        return publication_date
    else:
        return publication_date.replace(year=eff_date.year + 1)


def find_volume(year, title, part):
    """Annual editions have multiple volume numbers. Try to find the volume
    that we care about"""
    vol_num = 1
    volume = Volume(year, title, vol_num)
    while volume.exists:
        if volume.should_contain(part):
            return volume
        vol_num += 1
        volume = Volume(year, title, vol_num)
    return None
