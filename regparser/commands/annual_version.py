import logging
from datetime import date

import click

from regparser.commands.annual_editions import encoded_tree
from regparser.commands.fetch_annual_edition import source_file
from regparser.history.annual import find_volume
from regparser.notice.fake import build as build_fake_notice
from regparser.web.index.models import (CFRVersion, Document, SourceCollection,
                                        SourceFile)

_version_id = '{0}-annual-{1}'.format
logger = logging.getLogger(__name__)


def create_notice_if_needed(version_id, volume, cfr_part):
    notice_query = SourceFile.objects.filter(
        collection=SourceCollection.notice, file_name=version_id)
    if not notice_query.exists():
        build_fake_notice(version_id, volume.publication_date, volume.title,
                          cfr_part).save()


def create_document_if_needed(version, source, cfr_part):
    if not version.has_doc():
        version.doc = Document.objects.create(
            collection='gpo_cfr', label=cfr_part, source=source,
            version=version, contents=encoded_tree(source))


def create_where_needed(volume, cfr_part, source):
    version_id = _version_id(volume.year, cfr_part)

    create_notice_if_needed(version_id, volume, cfr_part)
    version, _ = CFRVersion.objects.get_or_create(
        cfr_title=volume.title, cfr_part=cfr_part, identifier=version_id,
        defaults=dict(source=source, effective=volume.publication_date,
                      fr_volume=1, fr_page=1)
    )
    create_document_if_needed(version, source, cfr_part)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.option('--year', type=int, default=None, help="Defaults to this year")
@click.pass_context
def annual_version(ctx, cfr_title, cfr_part, year):
    """Build a regulation tree for the most recent annual edition. This will
    also construct a corresponding, empty notice to match. The version will be
    marked as effective on the date of the last annual edition (which is not
    likely accurate)"""
    cfr_year = year or date.today().year
    vol = find_volume(cfr_year, cfr_title, cfr_part)
    if vol is None and year is None:
        logger.warning(
            "No annual edition for %s CFR %s, Year: %s. Trying %s.",
            cfr_title, cfr_part, cfr_year, cfr_year - 1)
        cfr_year -= 1
        vol = find_volume(cfr_year, cfr_title, cfr_part)

    if vol is None:
        logger.error("No annual edition for %s CFR %s, Year: %s",
                     cfr_title, cfr_part, cfr_year)
    else:
        logger.info("Getting annual version - %s CFR %s, Year: %s",
                    cfr_title, cfr_part, cfr_year)

        source = source_file(ctx, cfr_title, cfr_part, cfr_year)
        create_where_needed(vol, cfr_part, source)
