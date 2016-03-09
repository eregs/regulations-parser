import logging
from datetime import date

import click

from regparser.history.annual import find_volume
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.notice.fake import build as build_fake_notice
from regparser.tree import xml_parser


_version_id = '{}-annual-{}'.format
logger = logging.getLogger(__name__)


def process_if_needed(cfr_title, cfr_part, year, publication_date):
    """Review dependencies; if they're out of date, parse the annual edition
    into a tree and store that"""
    version_id = _version_id(year, cfr_part)
    annual_entry = entry.Annual(cfr_title, cfr_part, year)
    tree_entry = entry.Tree(cfr_title, cfr_part, version_id)
    # This is a little odd, but we use SxS as a source for "notice" data. This
    # will eventually be removed in favor of storing the version meta data
    # directly
    sxs_entry = entry.SxS(version_id)

    deps = dependency.Graph()
    deps.add(tree_entry, annual_entry)
    deps.validate_for(tree_entry)
    if deps.is_stale(tree_entry):
        tree = xml_parser.reg_text.build_tree(annual_entry.read().xml)
        tree_entry.write(tree)
        sxs_entry.write(build_fake_notice(
            version_id, publication_date.isoformat(), cfr_title, cfr_part))


def create_version_entry_if_needed(cfr_title, cfr_part, year,
                                   publication_date):
    """Only write the version entry if it doesn't already exist. If we
    overwrote one, we'd be invalidating all related trees, etc."""
    version_id = _version_id(year, cfr_part)
    version_entries = entry.Version(cfr_title, cfr_part)

    if version_id not in version_entries:
        (version_entries / version_id).write(
            Version(identifier=version_id, effective=publication_date,
                    published=publication_date))


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def current_version(cfr_title, cfr_part):
    """Build a regulation tree for the most recent annual edition. This will
    also construct a corresponding, empty notice to match. The version will be
    marked as effective on the date of the last annual edition (which is not
    likely accurate)"""
    year = date.today().year
    vol = find_volume(year, cfr_title, cfr_part)
    if vol is None:
        year -= 1
        vol = find_volume(year, cfr_title, cfr_part)

    logger.info("Getting current version - %s CFR %s, Year: %s",
                cfr_title, cfr_part, year)

    create_version_entry_if_needed(
        cfr_title, cfr_part, year, vol.publication_date)
    process_if_needed(cfr_title, cfr_part, year, vol.publication_date)
