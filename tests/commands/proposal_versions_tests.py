import pytest
from click.testing import CliRunner

from regparser.commands import proposal_versions
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML, TitlePartsRef
from regparser.web.index.models import CFRVersion


@pytest.mark.django_db
def test_missing_notice():
    """We should get an exception if the notice isn't present"""
    result = CliRunner().invoke(proposal_versions.proposal_versions, ['1111'])
    assert isinstance(result.exception, dependency.Missing)
    assert result.exception.dependency == str(entry.Notice('1111'))


@pytest.mark.django_db
def test_creates_version():
    entry.Notice('dddd').write(b'')
    notice_xml = NoticeXML(b'<ROOT/>')
    notice_xml.version_id = 'dddd'
    notice_xml.fr_volume = 1
    notice_xml.start_page = 2
    notice_xml.cfr_refs = [
        TitlePartsRef(11, [111, 222]), TitlePartsRef(22, [222, 333]),
    ]
    notice_xml.save()

    result = CliRunner().invoke(proposal_versions.proposal_versions, ['dddd'])
    assert result.exception is None
    versions = list(CFRVersion.objects.order_by('cfr_title', 'cfr_part'))
    assert versions[0].cfr_title == 11
    assert versions[0].cfr_part == 111
    assert versions[1].cfr_title == 11
    assert versions[1].cfr_part == 222
    assert versions[2].cfr_title == 22
    assert versions[2].cfr_part == 222
    assert versions[3].cfr_title == 22
    assert versions[3].cfr_part == 333
