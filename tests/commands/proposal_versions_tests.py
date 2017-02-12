import pytest
from click.testing import CliRunner
from mock import Mock, call

from regparser.commands import proposal_versions
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.notice.citation import Citation


@pytest.mark.django_db
def test_missing_notice():
    """We should get an exception if the notice isn't present"""
    result = CliRunner().invoke(proposal_versions.proposal_versions, ['1111'])
    assert isinstance(result.exception, dependency.Missing)
    assert result.exception.dependency == str(entry.Notice('1111'))


def test_creates_version(monkeypatch):
    monkeypatch.setattr(proposal_versions, 'entry', Mock())
    notice = proposal_versions.entry.Notice.return_value.read.return_value
    notice.fr_citation = Citation(1, 2)
    notice.cfr_ref_pairs = [(11, 111), (11, 222), (22, 222), (22, 333)]

    result = CliRunner().invoke(proposal_versions.proposal_versions, ['dddd'])
    assert result.exception is None
    assert proposal_versions.entry.Notice.call_args == call('dddd')
    assert proposal_versions.entry.Version.call_args_list == [
        call(11, 111, 'dddd'), call(11, 222, 'dddd'), call(22, 222, 'dddd'),
        call(22, 333, 'dddd')
    ]
    write_args = proposal_versions.entry.Version.return_value.write.call_args
    assert write_args == call(Version('dddd', None, Citation(1, 2)))
