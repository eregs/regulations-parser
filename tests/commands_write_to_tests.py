from contextlib import contextmanager
from datetime import date
import os
import tempfile
import shutil
from unittest import TestCase

from click.testing import CliRunner
from lxml import etree
from mock import Mock, patch
import pytest

from regparser.commands.write_to import transform_notice, write_to
from regparser.history.versions import Version
from regparser.index import entry
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.struct import Node


@pytest.mark.django_db
class CommandsWriteToTests(TestCase):
    def add_trees(self):
        """Add some versions to the index"""
        entry.Tree('12', '1000', 'v2').write(Node('v2'))
        entry.Tree('12', '1000', 'v3').write(Node('v3'))
        entry.Tree('12', '1000', 'v4').write(Node('v4'))
        entry.Tree('11', '1000', 'v5').write(Node('v5'))
        entry.Tree('12', '1001', 'v6').write(Node('v6'))

    def add_layers(self):
        """Add an assortment of layers to the index"""
        entry.Layer.cfr('12', '1000', 'v2', 'layer1').write({'1': 1})
        entry.Layer.cfr('12', '1000', 'v2', 'layer2').write({'2': 2})
        entry.Layer.cfr('12', '1000', 'v3', 'layer2').write({'2': 2})
        entry.Layer.cfr('12', '1000', 'v3', 'layer3').write({'3': 3})
        entry.Layer.cfr('11', '1000', 'v4', 'layer4').write({'4': 4})
        entry.Layer.cfr('12', '1001', 'v3', 'layer3').write({'3': 3})
        entry.Layer.preamble('555_55', 'layer5').write({'5': 5})

    def add_diffs(self):
        """Adds an uneven assortment of diffs between trees"""
        entry.Diff('12', '1000', 'v1', 'v2').write({'1': 2})
        entry.Diff('12', '1000', 'v2', 'v2').write({'2': 2})
        entry.Diff('12', '1000', 'v2', 'v1').write({'2': 1})
        entry.Diff('12', '1000', 'v0', 'v1').write({'0': 1})
        entry.Diff('11', '1000', 'v3', 'v1').write({'3': 1})
        entry.Diff('12', '1001', 'v3', 'v1').write({'3': 1})

    def add_notices(self):
        """Adds an uneven assortment of notices"""
        root_attrs = {
            "eregs-version-id": "v0",
            "fr-volume": 1,
            "fr-start-page": 2,
            "fr-end-page": 3
        }
        with XMLBuilder("ROOT", **root_attrs) as ctx:
            ctx.AGENCY("Agency")
            ctx.SUBJECT("Subj")
            ctx.DATES(**{'eregs-published-date': '2001-01-01'})
            with ctx.EREGS_CFR_REFS():
                ctx.EREGS_CFR_TITLE_REF(title=11)
        xml = ctx.xml
        entry.Notice('v0').write(NoticeXML(xml))

        etree.SubElement(xml.xpath('//EREGS_CFR_TITLE_REF')[0],
                         'EREGS_CFR_PART_REF', part='1000')
        xml.attrib['eregs-version-id'] = 'v1'
        entry.Notice('v1').write(NoticeXML(xml))

        xml.xpath('//EREGS_CFR_TITLE_REF')[0].attrib['title'] = '12'
        xml.attrib['eregs-version-id'] = 'v2'
        entry.Notice('v2').write(NoticeXML(xml))

        xml.attrib['eregs-version-id'] = 'v3'
        entry.Notice('v3').write(NoticeXML(xml))

    def file_exists(self, *parts):
        """Helper method to verify that a file was created"""
        path = os.path.join(self.tmpdir, *parts)
        return os.path.exists(path)

    def assert_file_exists(self, *parts):
        return self.assertTrue(self.file_exists(*parts))

    def assert_no_file(self, *parts):
        return self.assertFalse(self.file_exists(*parts))

    @contextmanager
    def integration(self):
        """Create a (small) set of files in the index. Handles setup and
        teardown of temporary directories"""
        cli = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        with cli.isolated_filesystem():
            self.add_trees()
            self.add_layers()
            self.add_diffs()
            self.add_notices()
            yield cli
        shutil.rmtree(self.tmpdir)

    def test_cfr_title_part(self):
        """Integration test that verifies only files associated with the
        requested CFR title/part are created"""
        with self.integration() as cli:
            cli.invoke(write_to, [self.tmpdir, '--cfr_title', '12',
                                  '--cfr_part', '1000'])

            self.assert_file_exists('regulation', '1000', 'v2')
            self.assert_file_exists('regulation', '1000', 'v3')
            self.assert_file_exists('regulation', '1000', 'v4')
            # these don't match the requested cfr title/part
            self.assert_no_file('regulation', '1000', 'v5')
            self.assert_no_file('regulation', '1001', 'v6')

            self.assert_file_exists('layer', 'layer1', 'cfr', 'v2', '1000')
            self.assert_file_exists('layer', 'layer2', 'cfr', 'v2', '1000')
            self.assert_file_exists('layer', 'layer2', 'cfr', 'v3', '1000')
            self.assert_file_exists('layer', 'layer3', 'cfr', 'v3', '1000')
            # these don't match the requested cfr title/part
            self.assert_no_file('layer', 'layer4', 'cfr', 'v4', '1000')
            self.assert_no_file('layer', 'layer2', 'cfr', 'v3', '1001')
            self.assert_no_file('layer', 'layer5', 'preamble', '555_55')

            self.assert_file_exists('diff', '1000', 'v1', 'v2')
            self.assert_file_exists('diff', '1000', 'v2', 'v2')
            self.assert_file_exists('diff', '1000', 'v2', 'v1')
            # these don't match the requested cfr title/part
            self.assert_no_file('diff', '1000', 'v3', 'v1')
            self.assert_no_file('diff', '1001', 'v3', 'v1')

            self.assert_file_exists('notice', 'v2')
            self.assert_file_exists('notice', 'v3')
            # these don't match the requested cfr title/part
            self.assert_no_file('notice', 'v0')
            self.assert_no_file('notice', 'v1')

    def test_cfr_title(self):
        """Integration test that verifies only files associated with the
        requested CFR title are created"""
        with self.integration() as cli:
            cli.invoke(write_to, [self.tmpdir, '--cfr_title', '12'])

            self.assert_no_file('regulation', '1000', 'v5')
            self.assert_file_exists('regulation', '1001', 'v6')
            self.assert_no_file('layer', 'layer4', 'cfr', 'v4', '1000')
            self.assert_file_exists('layer', 'layer3', 'cfr', 'v3', '1001')
            self.assert_no_file('layer', 'layer5', 'preamble', '555_55')
            self.assert_no_file('diff', '1000', 'v3', 'v1')
            self.assert_file_exists('diff', '1001', 'v3', 'v1')
            self.assert_no_file('notice', 'v0')
            self.assert_no_file('notice', 'v1')

    def test_no_params(self):
        """Integration test that all local files are written"""
        with self.integration() as cli:
            cli.invoke(write_to, [self.tmpdir])

            self.assert_file_exists('regulation', '1000', 'v5')
            self.assert_file_exists('layer', 'layer4', 'cfr', 'v4', '1000')
            self.assert_file_exists('layer', 'layer5', 'preamble', '555_55')
            self.assert_file_exists('diff', '1000', 'v3', 'v1')
            self.assert_file_exists('notice', 'v0')
            self.assert_file_exists('notice', 'v1')

    @patch('regparser.commands.write_to.add_footnotes')
    @patch('regparser.commands.write_to.process_sxs')
    def test_transform_notice(self, process_sxs, add_footnotes):
        """We should add version information and the SxS functions should be
        called"""
        with CliRunner().isolated_filesystem():
            entry.Version(11, 222, 'v1').write(
                Version('v1', date(2001, 1, 1), date(2002, 2, 2)))
            entry.Version(11, 222, 'v2').write(
                Version('v2', date(2002, 2, 2), date(2003, 3, 3)))
            entry.Version(11, 222, 'v3').write(
                Version('v3', date(2003, 3, 3), date(2004, 4, 4)))
            entry.Version(11, 223, 'v1').write(
                Version('v1', date(2001, 1, 1), date(2002, 2, 2)))
            entry.Version(11, 224, 'v1').write(
                Version('v1', date(2001, 1, 1), date(2002, 2, 2)))
            entry.Version(11, 222, 'proposal').write(
                Version('proposal', date(2003, 6, 6), None))
            entry.Version(11, 223, 'proposal').write(
                Version('proposal', date(2003, 6, 6), None))

            notice_xml = Mock()
            notice_xml.as_dict.return_value = {}
            notice_xml.version_id = 'proposal'
            notice_xml.cfr_ref_pairs = [(11, 222), (11, 223)]

            result = transform_notice(notice_xml)
            self.assertEqual(result['versions'], {
                222: {'left': 'v3', 'right': 'proposal'},
                223: {'left': 'v1', 'right': 'proposal'}})

            self.assertTrue(process_sxs.called)
            self.assertTrue(add_footnotes.called)
