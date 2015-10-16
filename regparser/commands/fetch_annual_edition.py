import click
from lxml import etree

from regparser import eregs_index
from regparser.history import annual


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('year', type=int)
def fetch_annual_edition(cfr_title, cfr_part, year):
    """Download an annual edition of a regulation"""
    path = eregs_index.Path('annual', cfr_title, cfr_part)
    volume = annual.find_volume(year, cfr_title, cfr_part)
    xml = volume.find_part_xml(cfr_part)
    path.write(year, etree.tostring(xml))
