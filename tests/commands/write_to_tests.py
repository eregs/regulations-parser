import os
from datetime import date

import pytest
from click.testing import CliRunner
from lxml import etree
from mock import Mock

from regparser.commands import write_to
from regparser.index import entry
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.struct import Node
from regparser.web.index.models import CFRVersion


def file_exists(base_dir, *parts):
    """Helper method to verify that a file was created"""
    path = os.path.join(base_dir, *parts)
    return os.path.exists(path)


def add_trees():
    """Add some versions to the index"""
    entry.Tree('12', '1000', 'v2').write(Node('v2'))
    entry.Tree('12', '1000', 'v3').write(Node('v3'))
    entry.Tree('12', '1000', 'v4').write(Node('v4'))
    entry.Tree('11', '1000', 'v5').write(Node('v5'))
    entry.Tree('12', '1001', 'v6').write(Node('v6'))


def add_layers():
    """Add an assortment of layers to the index"""
    entry.Layer.cfr('12', '1000', 'v2', 'layer1').write({'1': 1})
    entry.Layer.cfr('12', '1000', 'v2', 'layer2').write({'2': 2})
    entry.Layer.cfr('12', '1000', 'v3', 'layer2').write({'2': 2})
    entry.Layer.cfr('12', '1000', 'v3', 'layer3').write({'3': 3})
    entry.Layer.cfr('11', '1000', 'v4', 'layer4').write({'4': 4})
    entry.Layer.cfr('12', '1001', 'v3', 'layer3').write({'3': 3})
    entry.Layer.preamble('555_55', 'layer5').write({'5': 5})


def add_diffs():
    """Adds an uneven assortment of diffs between trees"""
    entry.Diff('12', '1000', 'v1', 'v2').write({'1': 2})
    entry.Diff('12', '1000', 'v2', 'v2').write({'2': 2})
    entry.Diff('12', '1000', 'v2', 'v1').write({'2': 1})
    entry.Diff('12', '1000', 'v0', 'v1').write({'0': 1})
    entry.Diff('11', '1000', 'v3', 'v1').write({'3': 1})
    entry.Diff('12', '1001', 'v3', 'v1').write({'3': 1})


def add_notices():
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
    entry.Notice('v0').write(b'')
    NoticeXML(xml).save()

    etree.SubElement(xml.xpath('//EREGS_CFR_TITLE_REF')[0],
                     'EREGS_CFR_PART_REF', part='1000')
    xml.attrib['eregs-version-id'] = 'v1'
    entry.Notice('v1').write(b'')
    NoticeXML(xml).save()

    xml.xpath('//EREGS_CFR_TITLE_REF')[0].attrib['title'] = '12'
    xml.attrib['eregs-version-id'] = 'v2'
    entry.Notice('v2').write(b'')
    NoticeXML(xml).save()

    xml.attrib['eregs-version-id'] = 'v3'
    entry.Notice('v3').write(b'')
    NoticeXML(xml).save()


@pytest.fixture
def integration():
    """Create a (small) set of files in the index."""
    add_trees()
    add_layers()
    add_diffs()
    add_notices()


@pytest.mark.django_db
@pytest.mark.usefixtures('integration')
def test_cfr_title_part(tmpdir):
    """Integration test that verifies only files associated with the
    requested CFR title/part are created"""
    root = str(tmpdir)
    CliRunner().invoke(write_to.write_to,
                       [root, '--cfr_title', '12', '--cfr_part', '1000'])

    assert file_exists(root, 'regulation', '1000', 'v2')
    assert file_exists(root, 'regulation', '1000', 'v3')
    assert file_exists(root, 'regulation', '1000', 'v4')
    # these don't match the requested cfr title/part
    assert not file_exists(root, 'regulation', '1000', 'v5')
    assert not file_exists(root, 'regulation', '1001', 'v6')

    assert file_exists(root, 'layer', 'layer1', 'cfr', 'v2', '1000')
    assert file_exists(root, 'layer', 'layer2', 'cfr', 'v2', '1000')
    assert file_exists(root, 'layer', 'layer2', 'cfr', 'v3', '1000')
    assert file_exists(root, 'layer', 'layer3', 'cfr', 'v3', '1000')
    # these don't match the requested cfr title/part
    assert not file_exists(root, 'layer', 'layer4', 'cfr', 'v4', '1000')
    assert not file_exists(root, 'layer', 'layer2', 'cfr', 'v3', '1001')
    assert not file_exists(root, 'layer', 'layer5', 'preamble', '555_55')

    assert file_exists(root, 'diff', '1000', 'v1', 'v2')
    assert file_exists(root, 'diff', '1000', 'v2', 'v2')
    assert file_exists(root, 'diff', '1000', 'v2', 'v1')
    # these don't match the requested cfr title/part
    assert not file_exists(root, 'diff', '1000', 'v3', 'v1')
    assert not file_exists(root, 'diff', '1001', 'v3', 'v1')

    assert file_exists(root, 'notice', 'v2')
    assert file_exists(root, 'notice', 'v3')
    # these don't match the requested cfr title/part
    assert not file_exists(root, 'notice', 'v0')
    assert not file_exists(root, 'notice', 'v1')


@pytest.mark.django_db
@pytest.mark.usefixtures('integration')
def test_cfr_title(tmpdir):
    """Integration test that verifies only files associated with the requested
    CFR title are created"""
    root = str(tmpdir)
    CliRunner().invoke(write_to.write_to, [root, '--cfr_title', '12'])

    assert not file_exists(root, 'regulation', '1000', 'v5')
    assert file_exists(root, 'regulation', '1001', 'v6')
    assert not file_exists(root, 'layer', 'layer4', 'cfr', 'v4', '1000')
    assert file_exists(root, 'layer', 'layer3', 'cfr', 'v3', '1001')
    assert not file_exists(root, 'layer', 'layer5', 'preamble', '555_55')
    assert not file_exists(root, 'diff', '1000', 'v3', 'v1')
    assert file_exists(root, 'diff', '1001', 'v3', 'v1')
    assert not file_exists(root, 'notice', 'v0')
    assert not file_exists(root, 'notice', 'v1')


@pytest.mark.django_db
@pytest.mark.usefixtures('integration')
def test_no_params(tmpdir):
    """Integration test that all local files are written"""
    root = str(tmpdir)
    CliRunner().invoke(write_to.write_to, [root])

    assert file_exists(root, 'regulation', '1000', 'v5')
    assert file_exists(root, 'layer', 'layer4', 'cfr', 'v4', '1000')
    assert file_exists(root, 'layer', 'layer5', 'preamble', '555_55')
    assert file_exists(root, 'diff', '1000', 'v3', 'v1')
    assert file_exists(root, 'notice', 'v0')
    assert file_exists(root, 'notice', 'v1')


@pytest.mark.django_db
def test_transform_notice(monkeypatch):
    """We should add version information and the SxS functions should be
    called"""
    monkeypatch.setattr(write_to, 'add_footnotes', Mock())
    monkeypatch.setattr(write_to, 'process_sxs', Mock())

    entry.Version(11, 222, 'v1').write(b'')
    CFRVersion.objects.create(
        identifier='v1', cfr_title=11, cfr_part=222,
        effective=date(2002, 2, 2), fr_volume=1, fr_page=1)
    entry.Version(11, 222, 'v2').write(b'')
    CFRVersion.objects.create(
        identifier='v2', cfr_title=11, cfr_part=222,
        effective=date(2003, 3, 3), fr_volume=2, fr_page=2)
    entry.Version(11, 222, 'v3').write(b'')
    CFRVersion.objects.create(
        identifier='v3', cfr_title=11, cfr_part=222,
        effective=date(2004, 4, 4), fr_volume=3, fr_page=3)
    entry.Version(11, 223, 'v1').write(b'')
    CFRVersion.objects.create(
        identifier='v1', cfr_title=11, cfr_part=223,
        effective=date(2002, 2, 2), fr_volume=1, fr_page=1)
    entry.Version(11, 224, 'v1').write(b'')
    CFRVersion.objects.create(
        identifier='v1', cfr_title=11, cfr_part=224,
        effective=date(2002, 2, 2), fr_volume=1, fr_page=1)
    entry.Version(11, 222, 'proposal').write(b'')
    CFRVersion.objects.create(
        identifier='proposal', cfr_title=11, cfr_part=222,
        fr_volume=4, fr_page=4)
    entry.Version(11, 223, 'proposal').write(b'')
    CFRVersion.objects.create(
        identifier='proposal', cfr_title=11, cfr_part=223,
        fr_volume=4, fr_page=4)

    notice_xml = Mock()
    notice_xml.as_dict.return_value = {}
    notice_xml.version_id = 'proposal'
    notice_xml.cfr_ref_pairs = [(11, 222), (11, 223)]

    result = write_to.transform_notice(notice_xml)
    assert result['versions'] == {222: {'left': 'v3', 'right': 'proposal'},
                                  223: {'left': 'v1', 'right': 'proposal'}}

    assert write_to.add_footnotes.called
    assert write_to.process_sxs.called
