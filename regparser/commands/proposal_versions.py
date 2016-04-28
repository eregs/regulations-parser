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

    for cfr_title, cfr_parts in notice.cfr_refs:
        for cfr_part in cfr_parts:
            entry.Version(cfr_title, cfr_part, doc_number).write(version)
