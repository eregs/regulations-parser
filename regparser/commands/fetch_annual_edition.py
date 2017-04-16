import click
from lxml import etree

from regparser.history import annual
from regparser.web.index.models import SourceCollection, SourceFile


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('year', type=int)
def fetch_annual_edition(cfr_title, cfr_part, year):
    """Download an annual edition of a regulation"""
    volume = annual.find_volume(year, cfr_title, cfr_part)
    xml = volume.find_part_xml(cfr_part).preprocess()
    attrs = {
        'collection': SourceCollection.annual.name,
        'file_name': SourceCollection.annual.format(cfr_title, cfr_part, year)
    }
    SourceFile.objects.filter(**attrs).delete()
    SourceFile.objects.create(
        contents=etree.tostring(xml.xml, encoding='UTF-8'), **attrs)


def source_file(ctx, cfr_title, cfr_part, year):
    """Retrieve the SourceFile associated with this title, part, and year. If
    it does not exist, run the appropriate command to grab it."""
    query = SourceFile.objects.filter(
        collection=SourceCollection.annual.name,
        file_name=SourceCollection.annual.format(cfr_title, cfr_part, year))
    if not query.exists():
        ctx.invoke(fetch_annual_edition, cfr_title, cfr_part, year)
    return query.get()
