"""Functions for processing the xml associated with the Federal Register's
notices"""
from collections import defaultdict
from datetime import date, datetime
import logging
import os
from urlparse import urlparse

from lxml import etree
import requests

from regparser.grammar.unified import notice_cfr_p
from regparser.history.delays import delays_in_sentence
from regparser.index import xml_sync
from regparser.notice.dates import fetch_dates
from regparser.tree.xml_parser.xml_wrapper import XMLWrapper
import settings

logger = logging.getLogger(__name__)


class NoticeXML(XMLWrapper):
    """Wrapper around a notice XML which provides quick access to the XML's
    encoded data fields"""
    def delays(self):
        """Pull out FRDelays found in the DATES tag"""
        dates_str = "".join(p.text for p in self.xpath(
            "(//DATES/P)|(//EFFDATE/P)"))
        return [delay for sent in dates_str.split('.')
                for delay in delays_in_sentence(sent)]

    def _set_date_attr(self, date_type, value):
        """Modify the XML tree so that it contains meta data for a date
        field. Accepts both strings and dates"""
        dates_tag = self.xpath('//DATES')
        if dates_tag:
            dates_tag = dates_tag[0]
        else:   # Tag wasn't present; create it
            dates_tag = etree.Element("DATES")
            self.xml.insert(0, dates_tag)
        if isinstance(value, date):
            value = value.isoformat()
        dates_tag.attrib["eregs-{}-date".format(date_type)] = value

    def derive_agencies(self, agencies=[]):
        """
        SIDE EFFECTS: this operates on the XML of the NoticeXML itself as well
        as returning some information.

        Adds elements to the NoticeXML to reflect information about the
        agencies connected to to notice.

        Looks for that information in a list of dicts passed in as
        ``agencies``, then adds it to the beginning of the XML as a set of
        elements that will look something like this::


            <EREGS_AGENCIES>
                <EREGS_AGENCY eregs-agency-name="x" eregs-agency-id="00"
                 eregs-agency-raw-name="X">
                    <EREGS_SUBAGENCY eregs-agency-name="y" eregs-agency-id="01"
                    eregs-agency-raw-name="Y"></EREGS_SUBAGENCY>
                </EREGS_AGENCY>
            </EREGS_AGENCIES>

        :arg list agencies: dict objects containing agency information,
                            including ``id``, ``parent_id``, ``name``, and
                            ``raw_name``.

        :rtype: dict
        :returns:   A dict of ``id``: ``defaultdict``, where the id is
                    the id of the agency, and the ``defaultdicts`` are nested
                    to reflect their parent/child relationships.
        """

        if not agencies:
            # The FR Notice XML doesn't tend to have all the metadata we need
            # contained within it, so don't try to parse that, just log an
            # error.
            logging.warn("Preprocessing notice: no agency metadata.")
            return {}

        # We need turn turn the references to parent_ids into a tree of dicts
        # that contain subagencies in children fields:
        agency_map = {agency["id"]:
                      defaultdict(list, agency) for agency in agencies}
        child_keys = []
        for key in agency_map:
            agency = agency_map[key]
            if agency.get("parent_id") and agency["parent_id"] in agency_map:
                agency_map[agency["parent_id"]]["children"].append(agency)
                child_keys.append(key)
        for key in child_keys:
            del agency_map[key]

        def add_children(el, children):
            """
            Given an element and a list of children, recursively appends
            children as EREGS_SUBAGENCY elements with the appropriate
            attributes, and appends their children to them, etc.

            :arg Element el:    The XML element to add child elements to.
                                Should be either EREGS_AGENCY or
                                EREGS_SUBAGENCY.
            :arg list children: dict objects containing the agency information.
                                Must have subagencies in `children` fields.

            :rtype: XML Element
            """
            if children:
                for agency in children:
                    sub_el = etree.Element("EREGS_SUBAGENCY")
                    sub_el.attrib["eregs-agency-name"] = str(agency["name"])
                    sub_el.attrib["eregs-agency-raw-name"] = str(
                        agency["raw_name"])
                    sub_el.attrib["eregs-agency-id"] = str(agency["id"])
                    if agency.get("children", []):
                        sub_el = add_children(sub_el, agency["children"])
                    el.append(sub_el)
            return el

        # Add the elements, starting with a parent ``EREGS_AGENCIES`` element.
        agencies_el = etree.Element("EREGS_AGENCIES")
        for agency_id in agency_map:
            agency = agency_map[agency_id]
            if not agency.get("parent_id"):
                agency_el = etree.Element("EREGS_AGENCY")
            else:
                agency_el = etree.Element("EREGS_SUBAGENCY")
            agency_el.attrib["eregs-agency-name"] = str(agency["name"])
            agency_el.attrib["eregs-agency-raw-name"] = str(agency["raw_name"])
            agency_el.attrib["eregs-agency-id"] = str(agency["id"])
            add_children(agency_el, agency.get("children", []))
            agencies_el.append(agency_el)

        self.xml.insert(0, agencies_el)
        return agency_map

    def derive_closing_date(self):
        """Attempt to parse comment closing date from DATES tags. Returns a
        datetime.date and sets the corresponding field"""
        dates = fetch_dates(self.xml) or {}
        if 'comments' in dates:
            comments = datetime.strptime(
                dates['comments'][0], "%Y-%m-%d").date()
            self.comments_close_on = comments
            return comments

    def derive_effective_date(self):
        """Attempt to parse effective date from DATES tags. Returns a
        datetime.date and sets the corresponding field"""
        dates = fetch_dates(self.xml) or {}
        if 'effective' in dates:
            effective = datetime.strptime(
                dates['effective'][0], "%Y-%m-%d").date()
            self.effective = effective
            return effective

    def _get_date_attr(self, date_type):
        """Pulls out the date set in `set_date_attr`, as a datetime.date. If
        not present, returns None"""
        value = self.xpath(".//DATES")[0].get('eregs-{}-date'.format(
            date_type))
        return datetime.strptime(value, "%Y-%m-%d").date()

    # --- Setters/Getters for specific fields. ---
    # We encode relevant information within the XML, but wish to provide easy
    # access

    @property
    def comments_close_on(self):
        return self._get_date_attr('comments-close-on')

    @comments_close_on.setter
    def comments_close_on(self, value):
        self._set_date_attr('comments-close-on', value)

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
        return int(self.xpath(".//PRTPAGE")[0].attrib['eregs-fr-volume'])

    @fr_volume.setter
    def fr_volume(self, value):
        for prtpage in self.xpath(".//PRTPAGE"):
            prtpage.attrib['eregs-fr-volume'] = str(value)

    @property
    def start_page(self):
        return int(self.xpath(".//PRTPAGE")[0].attrib["P"]) - 1

    @property
    def end_page(self):
        return int(self.xpath(".//PRTPAGE")[-1].attrib["P"])

    @property
    def version_id(self):
        return self.xml.attrib.get('eregs-version-id')

    @version_id.setter
    def version_id(self, value):
        self.xml.attrib['eregs-version-id'] = str(value)

    @property
    def cfr_parts(self):
        return [int(p) for p in fetch_cfr_parts(self.xml)]

    @property
    def cfr_titles(self):
        return list(sorted(set(
            int(notice_cfr_p.parseString(cfr_elm.text).cfr_title)
            for cfr_elm in self.xpath('//CFR'))))


def fetch_cfr_parts(notice_xml):
    """ Sometimes we need to read the CFR part numbers from the notice
        XML itself. This would need to happen when we've broken up a
        multiple-effective-date notice that has multiple CFR parts that
        may not be included in each date. """
    parts = []
    for cfr_elm in notice_xml.xpath('//CFR'):
        parts.extend(notice_cfr_p.parseString(cfr_elm.text).cfr_parts)
    return list(sorted(set(parts)))


def local_copies(url):
    """Use any local copies (potentially with modifications of the FR XML)"""
    parsed_url = urlparse(url)
    path = parsed_url.path.replace('/', os.sep)
    notice_dir_suffix, file_name = os.path.split(path)
    for xml_path in settings.LOCAL_XML_PATHS + [xml_sync.GIT_DIR]:
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
    local_notices = local_copies(notice_url)
    if local_notices:
        logger.info("using local xml for %s", notice_url)
        for local_notice_file in local_notices:
            with open(local_notice_file, 'r') as f:
                yield NoticeXML(f.read(), local_notice_file).preprocess()
    else:
        logger.info("fetching notice xml for %s", notice_url)
        content = requests.get(notice_url).content
        yield NoticeXML(content, notice_url).preprocess()


def xmls_for_url(notice_url):
    # @todo: remove the need for this function
    return [notice_xml.xml
            for notice_xml in notice_xmls_for_url('N/A', notice_url)]
