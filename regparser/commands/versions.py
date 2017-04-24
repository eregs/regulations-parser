import logging
import re
from collections import namedtuple
from operator import attrgetter, itemgetter

import click

from regparser.commands.preprocess_notice import preprocess_notice
from regparser.federalregister import fetch_notice_json
from regparser.index import entry
from regparser.notice.xml import NoticeXML
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile

logger = logging.getLogger(__name__)


def fetch_version_ids(cfr_title, cfr_part):
    """Returns a list of version ids after looking them up between the federal
    register and the local filesystem"""
    present_ids = [v.path[-1] for v in entry.Notice().sub_entries()]
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


def create_version(cfr_title, cfr_part, sources, version_id, delay=None):
    """Serialize a Version instance to disk"""
    notice_xml = NoticeXML(sources[version_id].xml())
    effective = notice_xml.effective if delay is None else delay.until
    delaying_source = None if delay is None else sources[delay.by]
    if effective:
        entry.Version(cfr_title, cfr_part, version_id).write(b'')
        CFRVersion.objects.create(
            identifier=version_id, source=sources[version_id],
            delaying_source=delaying_source, effective=effective,
            fr_volume=notice_xml.fr_citation.volume,
            fr_page=notice_xml.fr_citation.page, cfr_title=cfr_title,
            cfr_part=cfr_part
        )
    else:
        logger.warning("No effective date for this rule: %s. Skipping",
                       version_id)


def create_if_needed(cfr_title, cfr_part, source_files, delays_by_version):
    """All versions which are stale (either because they were never create or
    because their dependency has been updated) are written to disk. If any
    dependency is missing, an exception is raised"""
    source_by_id = {sf.file_name: sf for sf in source_files}
    for version_id in source_by_id.keys():
        exists = CFRVersion.objects.filter(
            identifier=version_id, cfr_title=cfr_title, cfr_part=cfr_part
        ).exists()
        if not exists:
            create_version(cfr_title, cfr_part, source_by_id, version_id,
                           delays_by_version.get(version_id))


def generate_source(version_id, ctx):
    """If the source file associated with this version doesn't exist yet,
    create it by calling preprocess_notice."""
    exists = SourceFile.objects.filter(
        collection=SourceCollection.notice.name, file_name=version_id
    ).exists()
    if not exists:
        ctx.invoke(preprocess_notice, document_number=version_id)
    return SourceFile.objects.get(
        collection=SourceCollection.notice.name, file_name=version_id)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.pass_context
def versions(ctx, cfr_title, cfr_part):
    """Find all Versions for a regulation. Accounts for locally modified
    notice XML and rules modifying the effective date of versions of a
    regulation"""
    cfr_title, cfr_part = str(cfr_title), str(cfr_part)

    logger.info("Finding versions")
    version_ids = fetch_version_ids(cfr_title, cfr_part)
    logger.debug("Versions found: %r", version_ids)

    source_files = [generate_source(v, ctx) for v in version_ids]
    # notices keyed by version_id
    delays_by_version = delays(source_files)
    create_if_needed(cfr_title, cfr_part, source_files, delays_by_version)
