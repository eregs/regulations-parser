import logging

import click

from regparser.index import entry
from regparser.notice.xml import NoticeXML

logger = logging.getLogger(__name__)


def parse_notice(xml_file_path):
    """Read the notice from the XML file; fill out any missing fields"""
    with open(xml_file_path, 'rb') as f:
        notice_xml = NoticeXML(f.read(), xml_file_path).preprocess()

    if has_requirements(notice_xml):
        notice_xml.derive_where_needed()
        return notice_xml


def has_requirements(notice_xml):
    """A few pieces of meta data only come from the Federal Register API. As
    we don't have access to that, we verify that the XML has it embedded"""
    if not notice_xml.version_id:
        logger.error("Missing version_id (eregs-version-id attribute on root)")
    elif not notice_xml.published:
        logger.error("Missing publish date (eregs-published-date attribute "
                     "on the DATES tag)")
    elif not notice_xml.fr_volume:
        logger.error("Missing volume (fr-volume attribute on root)")
    elif not notice_xml.start_page:
        logger.error("Missing volume (fr-start-page attribute on root)")
    else:
        return True


@click.command()
@click.argument('xml_file', type=click.Path(exists=True))
def import_notice(xml_file):
    """Convert XML file into a notice. May be used if manually creating a
    notice (e.g. from a Word doc). This command will also run a handful of
    validations on the XML"""
    notice_xml = parse_notice(xml_file)
    if notice_xml:
        notice_entry = entry.Notice(notice_xml.version_id)
        notice_entry.write(notice_xml)
