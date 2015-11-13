from collections import namedtuple
from datetime import date, datetime
import logging
import os
import re

import requests

from regparser.federalregister import fetch_notice_json
from regparser.history.delays import modify_effective_dates
from regparser.index import xml_sync
from regparser.notice.build import build_notice
from regparser.tree.xml_parser.xml_wrapper import XMLWrapper
import settings


CFR_BULK_URL = ("http://www.gpo.gov/fdsys/bulkdata/CFR/{year}/title-{title}/"
                + "CFR-{year}-title{title}-vol{volume}.xml")
CFR_PART_URL = ("http://www.gpo.gov/fdsys/pkg/"
                + "CFR-{year}-title{title}-vol{volume}/xml/"
                + "CFR-{year}-title{title}-vol{volume}-part{part}.xml")


class Volume(namedtuple('Volume', ['year', 'title', 'vol_num'])):
    def __init__(self, year, title, vol_num):
        super(Volume, self).__init__(year, title, vol_num)
        self.url = CFR_BULK_URL.format(year=year, title=title, volume=vol_num)
        self._response = requests.get(self.url, stream=True)
        self.exists = self._response.status_code == 200

    def should_contain(self, part):
        lines = self._response.iter_lines()
        line = next(lines)
        while '<PARTS>' not in line:
            line = next(lines)
        if not line:
            logging.warning('No <PARTS> in ' + self.url)
            return False

        match = re.match(r'.*parts? (\d+) to (\d+|end).*', line.lower())
        if match:
            start = int(match.group(1))
            if start > part:
                return False
            if match.group(2) == 'end':
                return True
            end = int(match.group(2))
            return end >= part
        else:
            logging.warning("Can't parse: " + line)
            return False

    def find_part_xml(self, part):
        """Pull the XML for an annual edition, first checking locally"""
        url = CFR_PART_URL.format(year=self.year, title=self.title,
                                  volume=self.vol_num, part=part)
        filename = url.split('/')[-1]
        for xml_path in settings.LOCAL_XML_PATHS + [xml_sync.GIT_DIR]:
            xml_path = os.path.join(xml_path, 'annual', filename)
            if os.path.isfile(xml_path):
                with open(xml_path) as f:
                    return XMLWrapper(f.read(), xml_path)
        response = requests.get(url)
        if response.status_code == 200:
            return XMLWrapper(response.content, url)


def annual_edition_for(title, notice):
    """Annual editions are published for different titles at different
    points throughout the year. Find the 'next' annual edition"""
    eff_date = datetime.strptime(notice['effective_on'], '%Y-%m-%d').date()
    return date_of_annual_after(title, eff_date).year


def date_of_annual_after(title, eff_date):
    """Annual editions are published for different titles at different points
    throughout the year. Return the date of the _first_ annual edition which
    should contain any changes on `eff_date`. This date may well be in the
    future"""
    if title <= 16:
        month_published = 1
    elif title <= 27:
        month_published = 4
    elif title <= 41:
        month_published = 7
    else:
        month_published = 10

    publication_date = date(eff_date.year, month_published, 1)
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


def first_notice_and_xml(title, part):
    """Find the first annual xml and its associated notice"""
    notices = [build_notice(title, part, n, fetch_xml=False)
               for n in fetch_notice_json(title, part, only_final=True)
               if n['full_text_xml_url'] and n['effective_on']]
    modify_effective_dates(notices)

    notices = sorted(notices,
                     key=lambda n: (n['effective_on'], n['publication_date']))

    years = {}
    for n in notices:
        year = annual_edition_for(title, n)
        years[year] = n

    for year, notice in sorted(years.iteritems()):
        volume = find_volume(year, title, part)
        if volume:
            part_xml = volume.find_part_xml(part)
            if part_xml is not None:
                return (notice, part_xml)
