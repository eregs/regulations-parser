from unittest import TestCase

from regparser import regs_gov
from regparser.test_utils.http_mixin import HttpMixin


class RegsGovTests(HttpMixin, TestCase):
    def test_proposal(self):
        """Should find the (one) proposal that matches, or none at all"""
        self.expect_json_http({'documents': [
            {'documentId': '1111', 'title': 'Some Title'},
            {'documentId': '2222', 'frNumber': 'AAAA', 'title': 'Some Title'},
            {'documentId': '3333', 'frNumber': 'BBBB', 'title': 'Some Title'}
        ]})
        self.assertIsNone(regs_gov.proposal('docket', 'CCCC'))
        proposal = regs_gov.proposal('docket', 'AAAA')
        self.assertEqual(proposal.regs_id, '2222')
        self.assertEqual(self.last_http_params().get('dct'),
                         ['PR'])
