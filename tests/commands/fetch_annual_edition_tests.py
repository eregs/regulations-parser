import pytest
from click.testing import CliRunner
from mock import Mock, call
from model_mommy import mommy

from regparser.commands import fetch_annual_edition
from regparser.tree.xml_parser.xml_wrapper import XMLWrapper
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile


@pytest.mark.django_db
def test_cascadingly_deletes(monkeypatch):
    """When running the command, we should expect all downstream models to get
    deleted"""
    monkeypatch.setattr(fetch_annual_edition, 'annual', Mock())
    # A mighty mock
    fetch_annual_edition.annual\
        .find_volume.return_value \
        .find_part_xml.return_value \
        .preprocess.return_value = XMLWrapper(b'<ROOT />')
    source = mommy.make(
        SourceFile, collection=SourceCollection.annual.name,
        file_name=SourceCollection.annual.format(11, 222, 2010))
    mommy.make(CFRVersion, source=source)

    assert SourceFile.objects.count() == 1
    assert CFRVersion.objects.count() == 1
    CliRunner().invoke(fetch_annual_edition.fetch_annual_edition,
                       ['11', '222', '2010'])
    assert SourceFile.objects.count() == 1
    assert CFRVersion.objects.count() == 0


@pytest.mark.django_db
def test_source_file_missing_dependency():
    """If the source XML isn't present, we should run a command to grab it"""
    ctx = Mock()

    def mock_invoke(command, cfr_title, cfr_part, year):
        file_name = SourceCollection.annual.format(cfr_title, cfr_part, year)
        mommy.make(SourceFile, collection=SourceCollection.annual.name,
                   file_name=file_name)
    ctx.invoke.side_effect = mock_invoke

    assert not SourceFile.objects.exists()
    fetch_annual_edition.source_file(ctx, 11, 222, 2010)

    assert SourceFile.objects.count() == 1
    assert ctx.invoke.call_args == call(
        fetch_annual_edition.fetch_annual_edition, 11, 222, 2010)

    fetch_annual_edition.source_file(ctx, 11, 222, 2010)
    assert SourceFile.objects.count() == 1      # doesn't change
