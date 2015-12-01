from collections import namedtuple
from datetime import date

import click

from regparser.history import annual
from regparser.index import dependency, entry
from regparser.tree import xml_parser


LastVersionInYear = namedtuple('LastVersionInYear', ['version_id', 'year'])


def last_versions(cfr_title, cfr_part):
    """Run through all known versions of this regulation and pull out versions
    which are the last to be included before an annual edition"""
    have_annual_edition = {}
    path = entry.Version(cfr_title, cfr_part)
    if len(path) == 0:
        raise click.UsageError("No versions found. Run `versions`?")
    for version_id in path:
        version = (path / version_id).read()
        pub_date = annual.date_of_annual_after(cfr_title, version.effective)
        if pub_date < date.today():
            have_annual_edition[pub_date.year] = version.identifier
    for year in sorted(have_annual_edition.keys()):
        yield LastVersionInYear(have_annual_edition[year], year)


def process_if_needed(cfr_title, cfr_part, last_versions):
    """Calculate dependencies between input and output files for these annual
    editions. If an output is missing or out of date, process it"""
    annual_path = entry.Annual(cfr_title, cfr_part)
    tree_path = entry.Tree(cfr_title, cfr_part)
    version_path = entry.Version(cfr_title, cfr_part)
    deps = dependency.Graph()

    for last_version in last_versions:
        deps.add(tree_path / last_version.version_id,
                 version_path / last_version.version_id)
        deps.add(tree_path / last_version.version_id,
                 annual_path / last_version.year)

    for last_version in last_versions:
        tree_entry = tree_path / last_version.version_id
        deps.validate_for(tree_entry)
        if deps.is_stale(tree_entry):
            input_entry = annual_path / last_version.year
            tree = xml_parser.reg_text.build_tree(input_entry.read().xml)
            tree_entry.write(tree)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def annual_editions(cfr_title, cfr_part):
    """Parse available annual editions for this reg. Cycles through all known
    versions and parses the annual edition XML when relevant"""
    versions = list(last_versions(cfr_title, cfr_part))
    process_if_needed(cfr_title, cfr_part, versions)
