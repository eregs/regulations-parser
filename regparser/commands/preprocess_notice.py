import click

from regparser import eregs_index, federalregister
from regparser.notice.build import split_doc_num
from regparser.notice.xml import notice_xmls_for_url


@click.command()
@click.argument('document_number')
def preprocess_notice(document_number):
    """Preprocess notice XML. Either fetch from the Federal Register or read a
    notice from disk. Apply some common transformations to it and output the
    resulting file(s). There may be more than one as documents might be split
    if they have multiple effective dates."""
    meta = federalregister.meta_data(
        document_number,
        ["effective_on", "full_text_xml_url", "publication_date", "volume"])
    notice_xmls = notice_xmls_for_url(document_number,
                                      meta['full_text_xml_url'])
    for notice_xml in notice_xmls:
        file_name = document_number
        notice_xml.published = meta['publication_date']
        notice_xml.fr_volume = meta['volume']

        if len(notice_xmls) > 1:
            effective_date = notice_xml.derive_effective_date()
            file_name = split_doc_num(document_number,
                                      effective_date.isoformat())
        elif 'effective_on' in meta:
            notice_xml.effective = meta['effective_on']
        else:
            notice_xml.derive_effective_date()

        notice_xml.version_id = file_name
        eregs_index.Path("notice_xml").write(file_name, notice_xml.xml_str())
