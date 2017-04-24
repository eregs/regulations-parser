import logging

import click

from regparser.federalregister import FULL_NOTICE_FIELDS, meta_data
from regparser.index import dependency, entry
from regparser.layer.section_by_section import SectionBySection
from regparser.notice.build import build_notice
from regparser.notice.xml import NoticeXML
from regparser.web.index.models import CFRVersion

logger = logging.getLogger(__name__)


def previous_sxs(cfr_title, cfr_part, stop_version):
    """The SxS layer relies on all notices that came before a particular
    version"""
    query = CFRVersion.objects.filter(
        cfr_title=cfr_title, cfr_part=cfr_part, effective__isnull=False)
    version_ids = [v.identifier for v in sorted(query)]
    for previous_version in version_ids:
        yield entry.Notice(previous_version)
        if previous_version == stop_version:
            break


def is_stale(cfr_title, cfr_part, version_id):
    """Modify and process dependency graph related to a single SxS layer"""
    deps = dependency.Graph()
    layer_entry = entry.Layer(cfr_title, cfr_part, version_id, 'analyses')

    # Layers depend on their associated tree
    deps.add(layer_entry, entry.Tree(cfr_title, cfr_part, version_id))
    # And on all notices which came before
    for sxs_entry in previous_sxs(cfr_title, cfr_part, version_id):
        deps.add(layer_entry, sxs_entry)

    deps.validate_for(layer_entry)
    return deps.is_stale(layer_entry)


def notice_dict(notice_xml):
    """The section-by-section layer assumes a particular format for notices"""
    meta = meta_data(notice_xml.version_id, FULL_NOTICE_FIELDS)
    notice_dict = build_notice(notice_xml.cfr_refs[0].title, None, meta,
                               xml_to_process=notice_xml.xml)[0]
    return notice_dict


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def sxs_layers(cfr_title, cfr_part):
    """Build SxS layers for all known versions."""
    logger.info("Build SxS layers - %s CFR %s", cfr_title, cfr_part)

    for tree_entry in entry.Tree(cfr_title, cfr_part).sub_entries():
        version_id = tree_entry.path[-1]
        if is_stale(cfr_title, cfr_part, version_id):
            tree = tree_entry.read()
            notices = []
            for notice_entry in previous_sxs(cfr_title, cfr_part, version_id):
                notice_xml = NoticeXML.from_db(notice_entry.path[-1])
                notices.append(notice_dict(notice_xml))
            layer_json = SectionBySection(tree, notices).build()
            entry.Layer.cfr(cfr_title, cfr_part, version_id, 'analyses').write(
                layer_json)
