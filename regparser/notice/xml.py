"""Functions for processing the xml associated with the Federal Register's
notices"""
from copy import deepcopy
from datetime import date, datetime
import logging
import os
from urlparse import urlparse

from lxml import etree
import requests

from regparser.notice import preprocessors
from regparser.notice.dates import fetch_dates
import settings


class NoticeXML(object):
    """Wrapper around a notice XML which provides quick access to the XML's
    encoded data fields"""
    def __init__(self, xml):
        """Includes automatic conversion from string and a deep copy for
        safety"""
        if isinstance(xml, basestring):
            self._xml = etree.fromstring(xml)
        else:
            self._xml = deepcopy(xml)

    def preprocess(self):
        """Unfortunately, the notice xml is often inaccurate. This function
        attempts to fix some of those (general) flaws. For specific issues, we
        tend to instead use the files in settings.LOCAL_XML_PATHS"""

        for preprocessor in preprocessors.ALL:
            preprocessor().transform(self._xml)

        return self

    def xml_str(self):
        return etree.tostring(self._xml, pretty_print=True)

    def _set_date_attr(self, date_type, value):
        """Modify the XML tree so that it contains meta data for a date
        field. Accepts both strings and dates"""
        dates_tag = self._xml.xpath('//DATES')
        if dates_tag:
            dates_tag = dates_tag[0]
        else:   # Tag wasn't present; create it
            dates_tag = etree.Element("DATES")
            self._xml.insert(0, dates_tag)
        if isinstance(value, date):
            value = value.isoformat()
        dates_tag.attrib["eregs-{}-date".format(date_type)] = value

    def derive_effective_date(self):
        """Attempt to parse effective date from DATES tags. Raises exception
        if it cannot. Also sets the field. Returns a datetime.date"""
        dates = fetch_dates(self._xml) or {}
        if 'effective' not in dates:
            raise Exception(
                "Could not derive effective date for notice {}".format(
                    self.version_id))
        effective = datetime.strptime(dates['effective'][0], "%Y-%m-%d").date()
        self.effective = effective
        return effective

    def _get_date_attr(self, date_type):
        """Pulls out the date set in `set_date_attr`, as a datetime.date. If
        not present, returns None"""
        value = self._xml.xpath(".//DATES")[0].get('eregs-{}-date'.format(
            date_type))
        return datetime.strptime(value, "%Y-%m-%d").date()

    # --- Setters/Getters for specific fields. ---
    # We encode relevant information within the XML, but wish to provide easy
    # access

    @property
    def effective(self):
        return self._get_date_attr('effective')

    @effective.setter
    def effective(self, value):
        self._set_date_attr('effective', value)

    @property
    def published(self):
        return self._get_date_attr('published')

    @published.setter
    def published(self, value):
        self._set_date_attr('published', value)

    @property
    def fr_volume(self):
        return int(self._xml.xpath(".//PRTPAGE")[0].attrib['eregs-fr-volume'])

    @fr_volume.setter
    def fr_volume(self, value):
        for prtpage in self._xml.xpath(".//PRTPAGE"):
            prtpage.attrib['eregs-fr-volume'] = str(value)

    @property
    def start_page(self):
        return int(self._xml.xpath(".//PRTPAGE")[0].attrib["P"]) - 1

    @property
    def end_page(self):
        return int(self._xml.xpath(".//PRTPAGE")[-1].attrib["P"])

    @property
    def version_id(self):
        return self._xml.attrib.get('eregs-version-id')

    @version_id.setter
    def version_id(self, value):
        self._xml.attrib['eregs-version-id'] = str(value)


def local_copies(url):
    """Use any local copies (potentially with modifications of the FR XML)"""
    parsed_url = urlparse(url)
    path = parsed_url.path.replace('/', os.sep)
    notice_dir_suffix, file_name = os.path.split(path)
    for xml_path in settings.LOCAL_XML_PATHS:
        if os.path.isfile(xml_path + path):
            return [xml_path + path]
        else:
            prefix = file_name.split('.')[0]
            notice_directory = xml_path + notice_dir_suffix
            notices = []
            if os.path.exists(notice_directory):
                notices = os.listdir(notice_directory)

            relevant_notices = [os.path.join(notice_directory, n)
                                for n in notices if n.startswith(prefix)]
            if relevant_notices:
                return relevant_notices
    return []


def notice_xmls_for_url(doc_num, notice_url):
    """Find, preprocess, and return the XML(s) associated with a particular FR
    notice url"""
    notice_strs = []
    local_notices = local_copies(notice_url)
    if local_notices:
        logging.info("using local xml for %s", notice_url)
        for local_notice_file in local_notices:
            with open(local_notice_file, 'r') as f:
                notice_strs.append(f.read())
    else:
        logging.info("fetching notice xml for %s", notice_url)
        notice_strs.append(requests.get(notice_url).content)

    return [NoticeXML(xml_str).preprocess() for xml_str in notice_strs]


def xmls_for_url(notice_url):
    # @todo: remove the need for this function
    return [notice_xml._xml
            for notice_xml in notice_xmls_for_url('N/A', notice_url)]
