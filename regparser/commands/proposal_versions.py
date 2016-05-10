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
    version = Version(doc_number, notice.published, None)

    cfr_pairs = [(ref.title, part)
                 for ref in notice.cfr_refs for part in ref.parts]
    for cfr_title, cfr_part in cfr_pairs:
        version_entry = entry.Version(cfr_title, cfr_part, doc_number)
        if not version_entry.exists() or version_entry.read() != version:
            version_entry.write(version)
