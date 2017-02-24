import logging
import re
from collections import namedtuple
from operator import attrgetter, itemgetter

import click

from regparser.federalregister import fetch_notice_json
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile

logger = logging.getLogger(__name__)


def fetch_version_ids(cfr_title, cfr_part, notice_dir):
    """Returns a list of version ids after looking them up between the federal
    register and the local filesystem"""
    present_ids = [v.path[-1] for v in notice_dir.sub_entries()]
    final_rules = fetch_notice_json(cfr_title, cfr_part, only_final=True)

    version_ids = []
    pair_fn = itemgetter('document_number', 'full_text_xml_url')
    for fr_id, xml_url in map(pair_fn, final_rules):
        if xml_url:
            # Version_id concatenated with the date
            regex = re.compile(re.escape(fr_id) + r"_\d{8}")
            split_entries = [vid for vid in present_ids if regex.match(vid)]
            # Add either the split entries or the original version_id
            version_ids.extend(split_entries or [fr_id])
        else:
            logger.warning("No XML for %s; skipping", fr_id)

    return version_ids


Delay = namedtuple('Delay', ['by', 'until'])


def delays(source_files):
    """Find all changes to effective dates. Return the latest change to each
    version of the regulation"""
    notice_xmls = [NoticeXML(sf.xml()) for sf in source_files]
    delay_map = {}
    # Sort so that later modifications override earlier ones
    for delayer in sorted(notice_xmls, key=attrgetter('fr_citation')):
        for delay in delayer.delays():
            for delayed in filter(delay.modifies_notice_xml, notice_xmls):
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


def write_to_disk(cfr_title, cfr_part, sources, version_id, delay=None):
    """Serialize a Version instance to disk"""
    notice_xml = NoticeXML(sources[version_id].xml())
    effective = notice_xml.effective if delay is None else delay.until
    delaying_source = None if delay is None else sources[delay.by]
    if effective:
        entry.Version(cfr_title, cfr_part, notice_xml.version_id).write(b'')
        CFRVersion.objects.filter(
            identifier=notice_xml.version_id, cfr_title=cfr_title,
            cfr_part=cfr_part).delete()
        CFRVersion.objects.create(
            identifier=notice_xml.version_id, source=sources[version_id],
            delaying_source=delaying_source, effective=effective,
            fr_volume=notice_xml.fr_citation.volume,
            fr_page=notice_xml.fr_citation.page, cfr_title=cfr_title,
            cfr_part=cfr_part
        )
    else:
        logger.warning("No effective date for this rule: %s. Skipping",
                       notice_xml.version_id)


def write_if_needed(cfr_title, cfr_part, source_files, delays_by_version):
    """All versions which are stale (either because they were never create or
    because their dependency has been updated) are written to disk. If any
    dependency is missing, an exception is raised"""
    source_by_id = {sf.file_name: sf for sf in source_files}
    version_dir = entry.Version(cfr_title, cfr_part)
    deps = generate_dependencies(version_dir, source_by_id.keys(),
                                 delays_by_version)
    for version_id in source_by_id.keys():
        version_entry = version_dir / version_id
        deps.validate_for(version_entry)
        if deps.is_stale(version_entry):
            write_to_disk(cfr_title, cfr_part, source_by_id, version_id,
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

    source_files = [
        SourceFile.objects.get(
            collection=SourceCollection.notice.name, file_name=version_id)
        for version_id in version_ids
    ]
    # notices keyed by version_id
    delays_by_version = delays(source_files)
    write_if_needed(cfr_title, cfr_part, source_files, delays_by_version)
