import logging

import click

from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.tree.gpo_cfr.builder import build_tree
from regparser.web.index.models import CFRVersion, SourceCollection, SourceFile

logger = logging.getLogger(__name__)


def regtext_for_part(notice_xml, cfr_title, cfr_part):
    """Filter to only the REGTEXT in question"""
    xpath = './/REGTEXT[@TITLE="{0}" and @PART="{1}"]'.format(
        cfr_title, cfr_part)
    matches = notice_xml.xpath(xpath)
    if not matches:
        logger.warning('No matching REGTEXT in this file')
    else:
        if len(matches) > 1:
            logger.warning('Multiple matching REGTEXTs; using the first')
        return matches[0]


def process_version_if_needed(cfr_title, cfr_part, version_id):
    """Creates and writes a version struct after validating the Notice has
    been created"""
    notice_entry = entry.Notice(version_id)
    version_entry = entry.Version(cfr_title, cfr_part, version_id)

    deps = dependency.Graph()
    deps.add(version_entry, notice_entry)
    deps.validate_for(version_entry)

    if deps.is_stale(version_entry):
        source = SourceFile.objects.get(
            collection=SourceCollection.notice.name, file_name=version_id
        )
        notice_xml = NoticeXML(source.xml())
        version_entry.write(b'')
        CFRVersion.objects.create(
            identifier=version_id, source=source, cfr_title=cfr_title,
            cfr_part=cfr_part, effective=notice_xml.effective,
            fr_volume=notice_xml.fr_citation.volume,
            fr_page=notice_xml.fr_citation.page
        )


def process_tree_if_needed(cfr_title, cfr_part, version_id):
    """Creates and writes a regulation tree if the appropriate notice
    exists"""
    notice_entry = entry.Notice(version_id)
    tree_entry = entry.Tree(cfr_title, cfr_part, version_id)

    deps = dependency.Graph()
    deps.add(tree_entry, notice_entry)
    deps.validate_for(tree_entry)

    if deps.is_stale(tree_entry):
        notice_xml = NoticeXML.from_db(version_id)
        tree = build_tree(regtext_for_part(notice_xml, cfr_title, cfr_part))
        tree_entry.write(tree)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('version', type=str)
def full_issuance(cfr_title, cfr_part, version):
    """Create a full regulation tree from a notice"""
    process_version_if_needed(cfr_title, cfr_part, version)
    process_tree_if_needed(cfr_title, cfr_part, version)
