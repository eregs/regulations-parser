from datetime import date

import pytest
from lxml import etree
from mock import Mock

from regparser.commands import full_issuance
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.struct import Node
from regparser.web.index.models import CFRVersion


def test_regtext_for_part(monkeypatch):
    """Finds the correct xml"""
    logger = Mock()
    monkeypatch.setattr(full_issuance, 'logger', logger)
    with XMLBuilder() as ctx:
        ctx.THING('a')
        ctx.REGTEXT('b', TITLE='T1', PART='P1')
        with ctx.CONTAINER():
            ctx.REGTEXT('c', TITLE='T1', PART='P2')
        ctx.THING('d')
        ctx.REGTEXT('e', TITLE='T2', PART='P1')
        ctx.REGTEXT('T1-P1 again', TITLE='T1', PART='P1')

    assert full_issuance.regtext_for_part(ctx.xml, 'T1', 'P2').text == 'c'
    assert not logger.warning.called

    assert full_issuance.regtext_for_part(ctx.xml, 'T1', 'P1').text == 'b'
    assert logger.warning.called
    logger.reset_mock()

    assert full_issuance.regtext_for_part(ctx.xml, 'T1', 'P3') is None
    assert logger.warning.called


@pytest.mark.django_db
@pytest.mark.parametrize('fn', [
    full_issuance.process_version_if_needed,
    full_issuance.process_tree_if_needed
])
def test_process_without_notice(fn):
    """Processing depends on a Notice"""
    with pytest.raises(dependency.Missing):
        fn('111', '222', 'version')


@pytest.mark.django_db
def test_process_version_if_needed_success():
    """If the requirements are present we should write the version data"""
    notice_xml = NoticeXML(XMLBuilder().xml)
    notice_xml.version_id = 'vvv'
    notice_xml.effective = date(2001, 1, 1)
    notice_xml.fr_volume = 2
    notice_xml.start_page = 3
    entry.Notice('vvv').write(b'')
    notice_xml.save()

    full_issuance.process_version_if_needed('111', '222', 'vvv')

    version = CFRVersion.objects.get()
    assert version.identifier == 'vvv'
    assert version.effective == date(2001, 1, 1)
    assert version.fr_volume == 2
    assert version.fr_page == 3
    assert version.cfr_title == 111
    assert version.cfr_part == 222


@pytest.mark.django_db
def test_process_tree_if_needed_success(monkeypatch):
    """If the requirements are present we should call tree-parsing function"""
    mock_regtext = Mock(return_value=Node('root'))
    monkeypatch.setattr(full_issuance, 'build_tree', mock_regtext)
    with XMLBuilder() as ctx:
        ctx.REGTEXT(TITLE=1, PART=2)
    entry.Notice('vvv').write(b'')
    notice_xml = NoticeXML(ctx.xml)
    notice_xml.version_id = 'vvv'
    notice_xml.save()

    full_issuance.process_tree_if_needed('1', '2', 'vvv')

    result = entry.Tree('1', '2', 'vvv').read()
    assert result.text == 'root'
    xml_given = mock_regtext.call_args[0][0]
    assert etree.tostring(xml_given) == etree.tostring(ctx.xml[0])
