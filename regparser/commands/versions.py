from collections import namedtuple
import logging
from operator import attrgetter, itemgetter
import re

import click

from regparser.federalregister import fetch_notice_json
from regparser.history.versions import Version
from regparser.index import dependency, entry


logger = logging.getLogger(__name__)


def fetch_version_ids(cfr_title, cfr_part, notice_dir):
    """Returns a list of version ids after looking them up between the federal
    register and the local filesystem"""
    present_ids = [v.path[-1] for v in notice_dir.sub_entries()]
    final_rules = fetch_notice_json(cfr_title, cfr_part, only_final=True)

    version_ids = []
    for fr_id in map(itemgetter('document_number'), final_rules):
        # Version_id concatenated with the date
        regex = re.compile(re.escape(fr_id) + r"_\d{8}")
        split_entries = [vid for vid in present_ids if regex.match(vid)]
        # Add either the split entries or the original version_id
        version_ids.extend(split_entries or [fr_id])

    return version_ids


Delay = namedtuple('Delay', ['by', 'until'])


def delays(xmls):
    """Find all changes to effective dates. Return the latest change to each
    version of the regulation"""
    delay_map = {}
    # Sort so that later modifications override earlier ones
    for delayer in sorted(xmls, key=attrgetter('published')):
        for delay in delayer.delays():
            for delayed in filter(delay.modifies_notice_xml, xmls):
                delay_map[delayed.version_id] = Delay(delayer.version_id,
                                                      delay.delayed_until)
    return delay_map


def generate_dependencies(version_dir, version_ids, delays_by_version):
    """Creates a dependency graph and adds all dependencies for input xml and
    delays between notices"""
    notice_dir = entry.Notice()
    deps = dependency.Graph()
    for version_id in version_ids:
        deps.add(version_dir / version_id, notice_dir / version_id)
    for delayed, delay in delays_by_version.items():
        deps.add(version_dir / delayed, notice_dir / delay.by)
    return deps


def write_to_disk(xml, version_entry, delay=None):
    """Serialize a Version instance to disk"""
    effective = xml.effective if delay is None else delay.until
    if effective:
        version = Version(identifier=xml.version_id, effective=effective,
                          published=xml.published)
        version_entry.write(version)
    else:
        logger.warning("No effective date for this rule: %s. Skipping",
                       xml.version_id)


def write_if_needed(cfr_title, cfr_part, version_ids, xmls, delays_by_version):
    """All versions which are stale (either because they were never create or
    because their dependency has been updated) are written to disk. If any
    dependency is missing, an exception is raised"""
    version_dir = entry.FinalVersion(cfr_title, cfr_part)
    deps = generate_dependencies(version_dir, version_ids, delays_by_version)
    for version_id in version_ids:
        version_entry = version_dir / version_id
        deps.validate_for(version_entry)
        if deps.is_stale(version_entry):
            write_to_disk(xmls[version_id], version_entry,
                          delays_by_version.get(version_id))


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def versions(cfr_title, cfr_part):
    """Find all Versions for a regulation. Accounts for locally modified
    notice XML and rules modifying the effective date of versions of a
    regulation"""
    cfr_title, cfr_part = str(cfr_title), str(cfr_part)
    notice_dir = entry.Notice()

    logger.info("Finding versions")
    version_ids = fetch_version_ids(cfr_title, cfr_part, notice_dir)
    logger.debug("Versions found: %r", version_ids)

    version_entries = [notice_dir / version_id for version_id in version_ids]
    # notices keyed by version_id
    xmls = {e.path[-1]: e.read() for e in version_entries if e.exists()}
    delays_by_version = delays(xmls.values())
    write_if_needed(cfr_title, cfr_part, version_ids, xmls, delays_by_version)
