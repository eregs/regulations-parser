import os.path
import tempfile
from unittest import TestCase

from lxml import etree
from mock import patch

from regparser.builder import (
    Builder, Checkpointer, NullCheckpointer)
from regparser.tree.struct import Node


class BuilderTests(TestCase):
    @patch('regparser.builder.merge_changes')
    @patch.object(Builder, '__init__')
    def test_revision_generator_notices(self, init, merge_changes):
        init.return_value = None
        b = Builder()   # Don't need parameters as init's been mocked out
        aaaa = {'document_number': 'aaaa', 'effective_on': '2012-12-12',
                'publication_date': '2011-11-11', 'changes': []}
        bbbb = {'document_number': 'bbbb', 'effective_on': '2012-12-12',
                'publication_date': '2011-11-12', 'changes': []}
        cccc = {'document_number': 'cccc', 'effective_on': '2013-01-01',
                'publication_date': '2012-01-01', 'changes': []}
        b.notices = [aaaa, bbbb, cccc]
        b.eff_notices = {'2012-12-12': [aaaa, bbbb], '2013-01-01': [cccc]}
        b.doc_number = 'aaaa'
        b.checkpointer = NullCheckpointer()
        tree = Node(label=['1111'])
        version_list = []
        notice_lists = []
        for notice, _, _, notices in b.revision_generator(tree):
            version_list.append(notice['document_number'])
            notice_lists.append(notices)
        self.assertEqual(['bbbb', 'cccc'], version_list)
        self.assertEqual(2, len(notice_lists))

        self.assertEqual(2, len(notice_lists[0]))
        self.assertTrue(aaaa in notice_lists[0])
        self.assertTrue(bbbb in notice_lists[0])

        self.assertEqual(3, len(notice_lists[1]))
        self.assertTrue(aaaa in notice_lists[1])
        self.assertTrue(bbbb in notice_lists[1])
        self.assertTrue(cccc in notice_lists[1])

    def test_determine_doc_number_fr(self):
        """Verify that a document number can be pulled out of an FR notice"""
        xml_str = """
        <RULE>
            <FRDOC>[FR Doc. 2011-31715 Filed 12-21-11; 8:45 am]</FRDOC>
            <BILCOD>BILLING CODE 4810-AM-P</BILCOD>
        </RULE>"""
        xml = etree.fromstring(xml_str)
        self.assertEqual(
            '2011-31715', Builder.determine_doc_number(xml, '00', '00'))

    @patch('regparser.builder.fetch_notice_json')
    def test_determine_doc_number_annual(self, fetch_notice_json):
        """The _latest_ document number pre-effective date should be pulled
        out of an annual edition of the reg"""
        fetch_notice_json.return_value = [
            {'document_number': '111-111', 'effective_on': '2011-01-01',
             'publication_date': '2011-01-01'},
            {'document_number': '222-222', 'effective_on': '2011-10-20',
             'publication_date': '2011-02-02'},
            {'document_number': '333-333', 'effective_on': '2011-10-20',
             'publication_date': '2011-03-03'},
            {'document_number': '444-444', 'effective_on': '2011-04-04',
             'publication_date': '2011-04-04'}]
        xml_str = """<?xml version="1.0"?>
        <?xml-stylesheet type="text/xsl" href="cfr.xsl"?>
        <CFRGRANULE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xsi:noNamespaceSchemaLocation="CFRMergedXML.xsd">
            <FDSYS>
                <CFRTITLE>12</CFRTITLE>
                <DATE>2013-01-01</DATE>
                <ORIGINALDATE>2012-01-01</ORIGINALDATE>
            </FDSYS>
        </CFRGRANULE>"""
        xml = etree.fromstring(xml_str)
        self.assertEqual(
            '333-333', Builder.determine_doc_number(xml, '12', '34'))
        args = fetch_notice_json.call_args
        self.assertEqual(('12', '34'), args[0])     # positional args
        self.assertEqual({'max_effective_date': '2012-01-01',
                          'only_final': True}, args[1])   # kw args

    @patch('regparser.builder.merge_changes')
    @patch.object(Builder, '__init__')
    def test_changes_in_sequence_skips(self, init, merge_changes):
        """Skips over notices which occurred _before_ our starting point"""
        init.return_value = None
        b = Builder()   # Don't need parameters as init's been mocked out
        aaaa = {'document_number': 'aaaa', 'effective_on': '2012-12-12',
                'publication_date': '2011-11-11', 'changes': []}
        bbbb = {'document_number': 'bbbb', 'effective_on': '2012-12-12',
                'publication_date': '2011-11-12', 'changes': []}
        cccc = {'document_number': 'cccc', 'effective_on': '2013-01-01',
                'publication_date': '2012-01-01', 'changes': []}
        b.eff_notices = {'2012-12-12': [aaaa, bbbb], '2013-01-01': [cccc]}
        b.doc_number = bbbb['document_number']
        changes = list(b.changes_in_sequence())
        self.assertEqual(len(changes), 1)
        self.assertEqual(cccc['document_number'], changes[0][0])
        self.assertEqual(cccc['document_number'],
                         merge_changes.call_args[0][0])


class CheckpointerTests(TestCase):
    def test_basic_serialization(self):
        """We should be able to store and retrieve an object. Verify that this
        is occurring outside of local memory by comparing to the original."""
        to_store = {"some": "value", 123: 456}
        cp = Checkpointer(tempfile.mkdtemp())
        cp.counter = 1
        cp._serialize("a-tag", to_store)
        to_store["some"] = "other"
        result = cp._deserialize("a-tag")
        self.assertEqual(result, {"some": "value", 123: 456})
        self.assertEqual(to_store, {"some": "other", 123: 456})

        cp.counter = 2
        cp._serialize("a-tag", to_store)
        to_store["some"] = "more"
        result = cp._deserialize("a-tag")
        self.assertEqual(result, {"some": "other", 123: 456})
        self.assertEqual(to_store, {"some": "more", 123: 456})
        cp.counter = 1
        result = cp._deserialize("a-tag")
        self.assertEqual(result, {"some": "value", 123: 456})

    def test_tree_serialization(self):
        """Trees have embedded XML, which doesn't serialize well"""
        tree = Node(
            text="top", label=["111"], title="Reg 111", children=[
                Node(text="inner", label=["111", "1"],
                     source_xml=etree.fromstring("""<tag>Hi</tag>"""))
            ])

        cp = Checkpointer(tempfile.mkdtemp())
        cp.checkpoint("a-tag", lambda: tree)    # saving
        cp._reset()
        loaded = cp.checkpoint("a-tag", None)   # would explode if not loaded

        self.assertEqual(repr(tree), repr(loaded))
        self.assertEqual(
            etree.tostring(tree.children[0].source_xml),
            etree.tostring(loaded.children[0].source_xml))

    def test_dont_load_later_elements(self):
        """If a checkpoint is executed, we should not load any later
        checkpoints. This allows a user to delete, say step 5, and effectively
        rebuild from that checkpoint."""
        cp = Checkpointer(tempfile.mkdtemp())
        self.assertEqual(cp.checkpoint("1", lambda: 1), 1)
        self.assertEqual(cp.checkpoint("2", lambda: 2), 2)
        self.assertEqual(cp.checkpoint("3", lambda: 3), 3)

        cp._reset()
        self.assertEqual(cp.checkpoint("1", lambda: -1), 1)
        self.assertEqual(cp.checkpoint("2", lambda: -2, force=True), -2)
        self.assertEqual(cp.checkpoint("3", lambda: -3), -3)

    def test_exception_reading(self):
        """If a file exists but is not the correct format, we expect
        deserialization to gracefully fail (rather than exploding)"""
        cp = Checkpointer(tempfile.mkdtemp())
        self.assertEqual(1, cp.checkpoint("1", lambda: 1))
        with open(cp._filename("1"), "w") as written_file:
            written_file.write("")
        cp._reset()
        # pickle will raise an exception, so we will recompute
        self.assertEqual(-1, cp.checkpoint("1", lambda: -1))

    def test_filename(self):
        """Verify that an appropriate file name is generated in an appropriate
        folder"""
        file_path = tempfile.mkdtemp() + os.path.join('some', 'depth', 'here')
        cp = Checkpointer(file_path)
        cp.counter = 25
        filename = cp._filename('A WeIrD TaG')
        self.assertTrue(os.path.join('some', 'depth', 'here') in filename)
        self.assertTrue('25' in filename)
        self.assertTrue('aweirdtag' in filename)

    def test_dirs_created(self):
        """If the full path does not exist, it is created"""
        file_path = tempfile.mkdtemp() + os.path.join('some', 'depth', 'here')
        Checkpointer(file_path)
        self.assertTrue(os.path.isdir(file_path))
