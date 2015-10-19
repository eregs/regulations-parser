# @todo - this is almost identical to parse_rule_changes as both are
# processing the parsed notice the same way. Once the concept of "changes" and
# SxS are split, the two programs will diverge
import click

from regparser import eregs_index
from regparser.notice.build import process_xml


@click.command()
@click.argument('document_number')
def fetch_sxs(document_number):
    """Fetch and parse Section-by-Section analyses.

    DOCUMENT_NUMBER is the identifier associated with a final rule. If a rule
    has been split, use the split identifiers, a.k.a. version ids"""
    sxs_entry = eregs_index.SxSEntry(document_number)
    notice_entry = eregs_index.NoticeEntry(document_number)

    deps = eregs_index.DependencyGraph()
    deps.add(sxs_entry, notice_entry)

    deps.validate_for(sxs_entry)
    # We don't check for staleness as we want to always execute when given a
    # specific file to process

    # @todo - break apart processing of SxS. We don't need all of the other
    # fields
    notice_xml = notice_entry.read()
    notice = process_xml(notice_xml.to_notice_dict(), notice_xml._xml)
    sxs_entry.write(notice)
