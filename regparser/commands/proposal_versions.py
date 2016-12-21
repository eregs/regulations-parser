import click

from regparser.history.versions import Version
from regparser.index import dependency, entry


@click.command()
@click.argument('doc_number')
def proposal_versions(doc_number):
    """Generate version entries associated with a proposal."""
    notice = entry.Notice(doc_number)
    if not notice.exists():
        raise dependency.Missing(str(notice), str(notice))

    notice = notice.read()
    version = Version(doc_number, notice.published, None, volume=notice.fr_volume, page=notice.start_page)

    for cfr_title, cfr_part in notice.cfr_ref_pairs:
        version_entry = entry.Version(cfr_title, cfr_part, doc_number)
        if not version_entry.exists() or version_entry.read() != version:
            version_entry.write(version)
