import click
from lxml import etree

from regparser import eregs_index, federalregister
from regparser.notice.dates import set_effective_date
from regparser.notice.build import split_doc_num
from regparser.notice.xml import xmls_for_url


@click.command()
@click.argument('document_number')
def preprocess_notice(document_number):
    """Preprocess notice XML. Either fetch from the Federal Register or read a
    notice from disk. Apply some common transformations to it and output the
    resulting file(s). There may be more than one as documents might be split
    if they have multiple effective dates."""
    meta = federalregister.meta_data(
        document_number, ["effective_on", "full_text_xml_url"])
    xmls = xmls_for_url(meta['full_text_xml_url'])
    for xml in xmls:
        if len(xmls) > 1:
            effective_date = set_effective_date(xml)
            file_name = split_doc_num(document_number, effective_date)
        else:
            set_effective_date(xml, meta.get('effective_on'))
            file_name = document_number

        xml_str = etree.tostring(xml, pretty_print=True)
        eregs_index.Path("notice_xml").write(file_name, xml_str)
