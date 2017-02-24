import logging
from collections import namedtuple

import click

from regparser.history import annual
from regparser.index import dependency, entry
from regparser.tree import gpo_cfr
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile

LastVersionInYear = namedtuple('LastVersionInYear', ['version_id', 'year'])
logger = logging.getLogger(__name__)


def last_versions(cfr_title, cfr_part):
    """Run through all known versions of this regulation and pull out versions
    which are the last to be included before an annual edition"""
    have_annual_edition = {}
    query = CFRVersion.objects.filter(cfr_title=cfr_title, cfr_part=cfr_part,
                                      effective__isnull=False)
    if not query.exists():
        raise click.UsageError("No versions found. Run `versions`?")
    for version in sorted(query):
        pub_date = annual.date_of_annual_after(cfr_title, version.effective)
        have_annual_edition[pub_date.year] = version.identifier
    for year in sorted(have_annual_edition):
        if annual.find_volume(year, cfr_title, cfr_part):
            yield LastVersionInYear(have_annual_edition[year], year)
        else:
            logger.warning("%s edition for %s CFR %s not published yet",
                           year, cfr_title, cfr_part)


def process_if_needed(cfr_title, cfr_part, last_version_list):
    """Calculate dependencies between input and output files for these annual
    editions. If an output is missing or out of date, process it"""
    annual_path = entry.Annual(cfr_title, cfr_part)
    tree_path = entry.Tree(cfr_title, cfr_part)
    version_path = entry.Version(cfr_title, cfr_part)
    deps = dependency.Graph()

    for last_version in last_version_list:
        deps.add(tree_path / last_version.version_id,
                 version_path / last_version.version_id)
        deps.add(tree_path / last_version.version_id,
                 annual_path / last_version.year)

    for last_version in last_version_list:
        tree_entry = tree_path / last_version.version_id
        deps.validate_for(tree_entry)
        if deps.is_stale(tree_entry):
            annual_xml = SourceFile.objects.filter(
                collection=SourceCollection.annual.name,
                file_name=SourceCollection.annual.format(
                    cfr_title, cfr_part, last_version.year)
            ).get().xml()
            tree = gpo_cfr.builder.build_tree(annual_xml)
            tree_entry.write(tree)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def annual_editions(cfr_title, cfr_part):
    """Parse available annual editions for this reg. Cycles through all known
    versions and parses the annual edition XML when relevant"""
    logger.info("Parsing annual editions - %s CFR %s", cfr_title, cfr_part)
    versions = list(last_versions(cfr_title, cfr_part))
    process_if_needed(cfr_title, cfr_part, versions)
