# @todo - this is almost identical to parse_rule_changes as both are
# processing the parsed notice the same way. Once the concept of "changes" and
# SxS are split, the two programs will diverge
import click

from regparser.commands.dependency_resolver import DependencyResolver
from regparser.federalregister import FULL_NOTICE_FIELDS, meta_data
from regparser.index import dependency, entry
from regparser.notice.build import build_notice


@click.command()
@click.argument('document_number')
def fetch_sxs(document_number):
    """Fetch and parse Section-by-Section analyses.

    DOCUMENT_NUMBER is the identifier associated with a final rule. If a rule
    has been split, use the split identifiers, a.k.a. version ids"""
    sxs_entry = entry.SxS(document_number)
    notice_entry = entry.Notice(document_number)

    deps = dependency.Graph()
    deps.add(sxs_entry, notice_entry)

    deps.validate_for(sxs_entry)
    # We don't check for staleness as we want to always execute when given a
    # specific file to process

    # @todo - break apart processing of SxS. We don't need all of the other
    # fields
    notice_xml = notice_entry.read()
    notice_meta = meta_data(document_number, FULL_NOTICE_FIELDS)
    notice = build_notice(notice_xml.cfr_refs[0].title, None, notice_meta,
                          xml_to_process=notice_xml.xml)[0]
    sxs_entry.write(notice)


class SxSResolver(DependencyResolver):
    PATH_PARTS = (entry.SxS.PREFIX, '(?P<doc_number>[a-zA-Z0-9-_]+)')

    def resolution(self):
        args = [self.match.group('doc_number')]
        return fetch_sxs.main(args, standalone_mode=False)
