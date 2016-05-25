from collections import namedtuple
import logging
import re

import click

from regparser.federalregister import fetch_notice_json
from regparser.history.versions import Version
from regparser.index import dependency, entry


logger = logging.getLogger(__name__)


def fetch_version_ids(cfr_title, cfr_part, notice_dir):
    """Returns a list of version ids after looking them up between the federal
    register and the local filesystem"""
    version_ids = []
    final_rules = fetch_notice_json(cfr_title, cfr_part, only_final=True)

    for document_number in (fr['document_number'] for fr in final_rules):
        # Document number followed by a date
        regex = re.compile(re.escape(document_number) + r"_\d{8}")
        version_ids.extend(
            [name for name in notice_dir if regex.match(name)] or
            [document_number])

    return version_ids


Delay = namedtuple('Delay', ['by', 'until'])


def delays(xmls):
    """Find all changes to effective dates. Return the latest change to each
    version of the regulation"""
    delays = {}
    # Sort so that later modifications override earlier ones
    for delayer in sorted(xmls, key=lambda xml: xml.published):
        for delay in delayer.delays():
            for delayed in filter(lambda x: delay.modifies_notice_xml(x),
                                  xmls):
                delays[delayed.version_id] = Delay(delayer.version_id,
                                                   delay.delayed_until)
    return delays


def generate_dependencies(version_dir, version_ids, delays):
    """Creates a dependency graph and adds all dependencies for input xml and
    delays between notices"""
    notice_dir = entry.Notice()
    deps = dependency.Graph()
    for version_id in version_ids:
        deps.add(version_dir / version_id, notice_dir / version_id)
    for delayed, delay in delays.items():
        deps.add(version_dir / delayed, notice_dir / delay.by)
    return deps


class InvalidEffectiveDate(Exception):
    def __init__(self, version_id):
        self.version_id = version_id
        super(InvalidEffectiveDate, self).__init__(
            "No effective date for this rule: {}".format(version_id))


def write_to_disk(xml, version_entry, delay=None):
    """Serialize a Version instance to disk"""
    effective = xml.effective if delay is None else delay.until
    if not effective:
        raise InvalidEffectiveDate(xml.version_id)
    version = Version(identifier=xml.version_id, effective=effective,
                      published=xml.published)
    version_entry.write(version)


def write_if_needed(cfr_title, cfr_part, version_ids, xmls, delays):
    """All versions which are stale (either because they were never create or
    because their dependency has been updated) are written to disk. If any
    dependency is missing, an exception is raised"""
    version_dir = entry.FinalVersion(cfr_title, cfr_part)
    deps = generate_dependencies(version_dir, version_ids, delays)
    for version_id in version_ids:
        version_entry = version_dir / version_id
        deps.validate_for(version_entry)
        if deps.is_stale(version_entry):
            write_to_disk(xmls[version_id], version_entry,
                          delays.get(version_id))


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
    xmls = {version_id: (notice_dir / version_id).read()
            for version_id in version_ids if version_id in notice_dir}
    delays_by_version = delays(xmls.values())
    write_if_needed(cfr_title, cfr_part, version_ids, xmls, delays_by_version)
