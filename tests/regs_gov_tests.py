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

    def test_supporting_docs(self):
        """Should filter the results to the appropriate types"""
        self.expect_json_http({'documents': [
            dict(documentId='1', documentType='Notice', title='a'),
            dict(documentId='2', documentType='Other', title='b'),
            dict(documentId='3', documentType='Final Rule', title='c'),
            dict(documentId='4', documentType='Supporting & Related Material',
                 title='d')]})
        self.assertEqual(
            list(regs_gov.supporting_docs('docket')),
            [regs_gov.RegsGovDoc('2', 'b'), regs_gov.RegsGovDoc('4', 'd')])
