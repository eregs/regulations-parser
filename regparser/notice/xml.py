"""Functions for processing the xml associated with the Federal Register's
notices"""
from copy import deepcopy
import logging
import os
from urlparse import urlparse

from lxml import etree
import requests

from regparser.notice import preprocessors
import settings


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


def preprocess(notice_xml):
    """Unfortunately, the notice xml is often inaccurate. This function
    attempts to fix some of those (general) flaws. For specific issues, we
    tend to instead use the files in settings.LOCAL_XML_PATHS"""
    notice_xml = deepcopy(notice_xml)   # We will be destructive

    for preprocessor in preprocessors.ALL:
        preprocessor().transform(notice_xml)

    return notice_xml


def xmls_for_url(notice_url):
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

    process = lambda xml_str: preprocess(etree.fromstring(xml_str))
    return [process(xml_str) for xml_str in notice_strs]
