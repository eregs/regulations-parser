"""Functions for processing the xml associated with the Federal Register's
notices"""
from copy import deepcopy
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
    def __init__(self, version_id, xml):
        """Includes automatic conversion from string and a deep copy for
        safety"""
        if isinstance(xml, basestring):
            xml = etree.fromstring(xml)
        self.version_id = version_id
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

    def _set_date_attr(self, date_type, date_str):
        """Modify the XML tree so that it contains meta data for a date
        field."""
        dates_tag = self._xml.xpath('//DATES')
        if dates_tag:
            dates_tag = dates_tag[0]
        else:   # Tag wasn't present; create it
            dates_tag = etree.Element("DATES")
            self._xml.insert(0, dates_tag)
        dates_tag.attrib["eregs-{}-date".format(date_type)] = date_str
        return date_str

    def derive_effective_date(self):
        """Attempt to parse effective date from DATES tags. Raises exception
        if it cannot. Also sets the field"""
        dates = fetch_dates(self._xml) or {}
        if 'effective' not in dates:
            raise Exception(
                "Could not derive effective date for notice {}".format(
                    self.version_id))
        effective = dates['effective'][0]
        self.effective = effective
        return effective

    def _get_date_attr(self, date_type):
        """Pulls out the date set in `set_date_attr`. If not present, returns
        None"""
        return self._xml.xpath(".//DATES")[0].get('eregs-{}-date'.format(
            date_type))

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
        return int(self._xml.attrib['eregs-fr-volume'])

    @fr_volume.setter
    def fr_volume(self, value):
        self._xml.attrib['eregs-fr-volume'] = str(value)

    @property
    def start_page(self):
        return int(self._xml.xpath(".//PRTPAGE")[0].attrib["P"]) - 1

    @property
    def end_page(self):
        return int(self._xml.xpath(".//PRTPAGE")[-1].attrib["P"])


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

    return [NoticeXML(doc_num, xml_str).preprocess()
            for xml_str in notice_strs]


def xmls_for_url(notice_url):
    # @todo: remove the need for this function
    return [notice_xml._xml
            for notice_xml in notice_xmls_for_url('N/A', notice_url)]
