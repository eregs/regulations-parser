import logging
from collections import namedtuple

from regparser.index.http_cache import http_client
from regparser.web.settings.parser import REGS_GOV_API, REGS_GOV_KEY

REGS_GOV_DOC_API = REGS_GOV_API + 'documents.json'


logger = logging.getLogger(__name__)
RegsGovDoc = namedtuple('RegsGovDoc', ['regs_id', 'title'])


def docs(docket_id, filter_fn=None):
    """Fetch RegsGovDocs representing documents within this docket. Grab all
    types except public submissions. Use `filter_fn` to limit the results"""
    # Use a list for consistent ordering, which is useful for caching
    params = [('api_key', REGS_GOV_KEY), ('dktid', docket_id), ('rpp', 1000),
              ('sb', 'docId'), ('so', 'ASC'), ('dct', 'N+PR+FR+O+SR')]
    results = http_client().get(REGS_GOV_DOC_API, params=params).json()
    if results.get('error'):
        logger.warning("Error retrieving data from regs.gov: %s",
                       results['error'].get('message'))
    for doc_dict in results.get('documents', []):
        if filter_fn is None or filter_fn(doc_dict):
            yield RegsGovDoc(doc_dict['documentId'], doc_dict['title'])


def proposal(docket_id, fr_doc_number):
    """If the requested Federal Register document is in this docket, return
    it"""
    for doc in docs(docket_id, lambda d: d.get('frNumber') == fr_doc_number):
        return doc


def supporting_docs(docket_id):
    types = ('Supporting & Related Material', 'Other')
    for doc in docs(docket_id, lambda d: d.get('documentType') in types):
        yield doc
