from collections import namedtuple

import requests

from settings import REGS_GOV_API, REGS_GOV_DOC_TPL, REGS_GOV_KEY
REGS_GOV_DOC_API = REGS_GOV_API + 'documents.json'


RegsGovDoc = namedtuple('RegsGovDoc', ['regs_id', 'fr_id', 'href', 'title'])


def docs(docket_id, doc_type=None):
    """Fetch RegsGovDocs representing documents within this docket"""
    params = {'api_key': REGS_GOV_KEY, 'dktid': docket_id, 'rpp': 1000,
              'sb': 'docId', 'so': 'ASC'}
    if doc_type:
        params['dct'] = doc_type
    results = requests.get(REGS_GOV_DOC_API, params=params).json()
    for doc_dict in results.get('documents', []):
        yield RegsGovDoc(
            doc_dict['documentId'], doc_dict.get('frNumber'),
            REGS_GOV_DOC_TPL.format(doc_id=doc_dict['documentId']),
            doc_dict['title'])


def proposal(docket_id, fr_doc_number):
    """If the requested Federal Register document is in this docket, return
    it"""
    for doc in docs(docket_id, doc_type='PR'):
        if doc.fr_id == fr_doc_number:
            return doc


def supporting_docs(docket_id):
    supporting = list(docs(docket_id, doc_type='SR'))
    other = list(docs(docket_id, doc_type='O'))
    return sorted(supporting + other)
