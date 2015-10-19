import click

from regparser import eregs_index
from regparser.notice.build import process_xml
from regparser.notice.encoder import AmendmentEncoder
from regparser.notice.xml import NoticeXML


@click.command()
@click.argument('document_number')
def parse_rule_changes(document_number):
    """Parse changes present in a single rule.

    DOCUMENT_NUMBER is the identifier associated with a final rule. If a rule
    has been split, use the split identifiers, a.k.a. version ids."""
    deps = eregs_index.DependencyGraph()
    deps.add(('rule_changes', document_number),
             ('notice_xml', document_number))
    encoder = AmendmentEncoder(sort_keys=True, indent=4,
                               separators=(', ', ': '))

    deps.validate_for('rule_changes', document_number)
    # We don't check for staleness as we want to always execute when given a
    # specific file to process

    # @todo - break apart processing of amendments/changes. We don't need
    # all of the other fields
    notice_xml = eregs_index.Path('notice_xml').read_xml(document_number)
    notice = process_xml(NoticeXML(notice_xml).to_notice_dict(),
                         notice_xml)
    eregs_index.Path('rule_changes').write(
        document_number, encoder.encode(notice))
