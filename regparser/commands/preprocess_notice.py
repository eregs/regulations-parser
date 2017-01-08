import click

from regparser import federalregister
from regparser.commands.dependency_resolver import DependencyResolver
from regparser.index import entry
from regparser.notice.build import split_doc_num
from regparser.notice.xml import TitlePartsRef, notice_xmls_for_url


def convert_cfr_refs(refs=None):
    """
    Get the references to CFR titles and parts out of the metadata.
    Return a list of TitlePartsRef objects grouped by title and
    sorted, for example::

        [{"title": 0, "part": 23}, {"title": 0, "part": 17}]

    Becomes::

        [TitlePartsRef(title="0", parts=["17", "23"])]

    :arg list refs: The list of title/part pairs; if empty, will create an
        empty ``EREGS_CFR_REFS`` element and return an empty list.
    :rtype: list
    :returns: Grouped & sorted list.
    """
    refs = refs or []
    # Group parts by title:
    refd = {r["title"]: [] for r in refs}
    for ref in refs:
        refd[ref["title"]].append(ref["part"])
    refs = [{u"title": k, "parts": refd[k]} for k in refd]
    # Sort parts and sort list by title:
    refs = [TitlePartsRef(r["title"], sorted(r["parts"], key=int))
            for r in refs]
    return sorted(refs, key=lambda x: int(x.title))


@click.command()
@click.argument('document_number')
def preprocess_notice(document_number):
    """Preprocess notice XML. Either fetch from the Federal Register or read a
    notice from disk. Apply some common transformations to it and output the
    resulting file(s). There may be more than one as documents might be split
    if they have multiple effective dates."""
    meta = federalregister.meta_data(
        document_number, [
            "agencies",
            "docket_ids",
            "effective_on",
            "cfr_references",
            "comments_close_on",
            "end_page",
            "full_text_xml_url",
            "html_url",
            "publication_date",
            "regulation_id_numbers",
            "start_page",
            "volume"
        ])
    notice_xmls = list(notice_xmls_for_url(meta['full_text_xml_url']))
    for notice_xml in notice_xmls:
        notice_xml.published = meta['publication_date']
        notice_xml.fr_volume = meta['volume']
        notice_xml.start_page = meta['start_page']
        notice_xml.end_page = meta['end_page']
        if meta.get('html_url'):
            notice_xml.fr_html_url = meta['html_url']
        if meta.get("comments_close_on"):
            notice_xml.comments_close_on = meta["comments_close_on"]
        if meta.get('regulation_id_numbers'):
            notice_xml.rins = meta['regulation_id_numbers']
        if meta.get('docket_ids'):
            notice_xml.docket_ids = meta['docket_ids']

        notice_xml.set_agencies(meta.get('agencies', []))

        cfr_refs = convert_cfr_refs(meta.get('cfr_references', []))
        if cfr_refs:
            notice_xml.cfr_refs = cfr_refs

        file_name = document_number
        if len(notice_xmls) > 1:
            effective_date = notice_xml.derive_effective_date()
            file_name = split_doc_num(document_number,
                                      effective_date.isoformat())
        elif meta.get('effective_on'):
            notice_xml.effective = meta['effective_on']

        notice_xml.version_id = file_name
        notice_xml.derive_where_needed()

        notice_entry = entry.Notice(file_name)
        notice_entry.write(notice_xml)


class NoticeResolver(DependencyResolver):
    PATH_PARTS = (entry.Notice.PREFIX, '(?P<doc_number>[a-zA-Z0-9-_]+)')

    def resolution(self):
        args = [self.match.group('doc_number')]
        return preprocess_notice.main(args, standalone_mode=False)
