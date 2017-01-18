"""Fetch data from the Federal Register

See https://www.federalregister.gov/developers/api/v1 - GET "search" method
"""
import logging

from regparser.index.http_cache import http_client

FR_BASE = "https://www.federalregister.gov"
API_BASE = FR_BASE + "/api/v1/"
FULL_NOTICE_FIELDS = [
    "cfr_references", "citation", "comments_close_on", "dates",
    "document_number", "effective_on", "end_page", "full_text_xml_url",
    "html_url", "publication_date", "regulation_id_numbers", "start_page",
    "type", "volume"]
logger = logging.getLogger(__name__)


def fetch_notice_json(cfr_title, cfr_part, only_final=False,
                      max_effective_date=None):
    """Search through all articles associated with this part. Right now,
    limited to 1000; could use paging to fix this in the future."""
    params = {
        "conditions[cfr][title]": cfr_title,
        "conditions[cfr][part]": cfr_part,
        "per_page": 1000,
        "order": "oldest",
        "fields[]": FULL_NOTICE_FIELDS}
    if only_final:
        params["conditions[type][]"] = 'RULE'
    if max_effective_date:
        params["conditions[effective_date][lte]"] = max_effective_date
    url = API_BASE + "articles"
    logger.info("Fetching notices - URL: %s Params: %r", url, params)
    response = http_client().get(url, params=params).json()
    logger.debug("Fetching notices response - %r", response)
    if 'results' in response:
        return response['results']
    else:
        return []


def meta_data(document_number, fields=None):
    """Return the requested meta data for a specific Federal Register
    document. Accounts for a bad document number by throwing an exception"""
    url = "{0}articles/{1}".format(API_BASE, document_number)
    params = {}     # default fields are generally good
    if fields:
        params["fields[]"] = fields
    response = http_client().get(url, params=params)
    response.raise_for_status()
    return response.json()
