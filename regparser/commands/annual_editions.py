import logging

import click

from regparser.commands.fetch_annual_edition import fetch_annual_edition
from regparser.history import annual
from regparser.tree import gpo_cfr
from regparser.tree.struct import FullNodeEncoder
from regparser.web.index.models import (CFRVersion, DocCollection,
                                        SourceCollection, SourceFile)

logger = logging.getLogger(__name__)


def last_versions(cfr_title, cfr_part):
    """Run through all known versions of this regulation and pull out versions
    which are the last to be included before an annual edition"""
    have_annual_edition = {}
    query = CFRVersion.objects.filter(
        cfr_title=cfr_title, cfr_part=cfr_part, effective__isnull=False)
    if not query.exists():
        raise click.UsageError("No versions found. Run `versions`?")
    for version in sorted(query):
        pub_date = annual.date_of_annual_after(cfr_title, version.effective)
        have_annual_edition[pub_date.year] = version
    for year in sorted(have_annual_edition):
        if annual.find_volume(year, cfr_title, cfr_part):
            yield have_annual_edition[year]
        else:
            logger.warning("%s edition for %s CFR %s not published yet",
                           year, cfr_title, cfr_part)


def source_file(ctx, cfr_title, cfr_part, year):
    """Retrieve the SourceFile associated with this title, part, and year. If
    it does not exist, run the appropriate command to grab it."""
    query = SourceFile.objects.filter(
        collection=SourceCollection.annual.name,
        file_name=SourceCollection.annual.format(cfr_title, cfr_part, year))
    if not query.exists():
        ctx.invoke(fetch_annual_edition, cfr_title, cfr_part, year)
    return query.get()


def encoded_tree(source):
    """Given a SourceFile, parse a Node tree and encode it into JSON bytes"""
    annual_xml = source.xml()
    tree = gpo_cfr.builder.build_tree(annual_xml)
    encoder = FullNodeEncoder(sort_keys=True, indent=4)
    return encoder.encode(tree).encode('utf-8')     # as bytes


def create_where_needed(ctx, cfr_title, cfr_part, last_version_list):
    """Parse and store any missing Documents associated with annual
    editions"""
    for version in last_version_list:
        year = annual.date_of_annual_after(cfr_title, version.effective).year
        source = source_file(ctx, cfr_title, cfr_part, year)
        if not version.docs.count():
            version.docs.create(
                collection=DocCollection.gpo_cfr.name, label=cfr_part,
                source=source_file(ctx, cfr_title, cfr_part, year),
                contents=encoded_tree(source)
            )


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.pass_context
def annual_editions(ctx, cfr_title, cfr_part):
    """Parse available annual editions for this reg. Cycles through all known
    versions and parses the annual edition XML when relevant"""
    logger.info("Parsing annual editions - %s CFR %s", cfr_title, cfr_part)
    versions = list(last_versions(cfr_title, cfr_part))
    create_where_needed(ctx, cfr_title, cfr_part, versions)
