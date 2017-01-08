import logging

import click

from regparser.index import dependency, entry
from regparser.notice.preamble import convert_id, parse_preamble

logger = logging.getLogger(__name__)


@click.command()
@click.argument('doc_number')
def notice_preamble(doc_number):
    """Pull down and parse the preamble from this notice."""
    logger.info("Parsing Preamble for %s", doc_number)
    preamble_path = entry.Preamble(convert_id(doc_number))
    notice_path = entry.Notice(doc_number)

    deps = dependency.Graph()
    deps.add(preamble_path, notice_path)
    deps.validate_for(preamble_path)

    if deps.is_stale(preamble_path):
        preamble = parse_preamble(notice_path.read())
        preamble_path.write(preamble)
