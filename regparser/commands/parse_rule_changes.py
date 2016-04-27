import click

from regparser.commands.dependency_resolver import DependencyResolver
from regparser.index import dependency, entry
from regparser.notice.amendments import fetch_amendments


@click.command()
@click.argument('document_number')
def parse_rule_changes(document_number):
    """Parse changes present in a single rule.

    DOCUMENT_NUMBER is the identifier associated with a final rule. If a rule
    has been split, use the split identifiers, a.k.a. version ids."""
    rule_entry = entry.RuleChanges(document_number)
    notice_entry = entry.Notice(document_number)

    deps = dependency.Graph()
    deps.add(rule_entry, notice_entry)

    deps.validate_for(rule_entry)
    # We don't check for staleness as we want to always execute when given a
    # specific file to process

    notice_xml = notice_entry.read()
    amendments = fetch_amendments(notice_xml.xml)
    if amendments:
        rule_entry.write({'amendments': amendments})
    else:
        rule_entry.write({})


class RuleChangesResolver(DependencyResolver):
    PATH_PARTS = entry.RuleChanges.PREFIX + (
        '(?P<doc_number>[a-zA-Z0-9-_]+)',)

    def resolution(self):
        args = [self.match.group('doc_number')]
        return parse_rule_changes.main(args, standalone_mode=False)
