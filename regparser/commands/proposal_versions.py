import click

from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile


@click.command()
@click.argument('doc_number')
def proposal_versions(doc_number):
    """Generate version entries associated with a proposal."""
    notice = entry.Notice(doc_number)
    if not notice.exists():
        raise dependency.Missing(str(notice), str(notice))

    source = SourceFile.objects.get(
        collection=SourceCollection.notice.name, file_name=doc_number)
    notice = NoticeXML(source.xml())

    for cfr_title, cfr_part in notice.cfr_ref_pairs:
        entry.Version(cfr_title, cfr_part, doc_number).write(b'')
        CFRVersion.objects.filter(
            identifier=doc_number, cfr_title=cfr_title, cfr_part=cfr_part
        ).delete()
        CFRVersion.objects.create(
            identifier=doc_number, source=source, cfr_title=cfr_title,
            cfr_part=cfr_part, fr_volume=notice.fr_citation.volume,
            fr_page=notice.fr_citation.page
        )
