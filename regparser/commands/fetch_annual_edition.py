import click

from regparser import eregs_index
from regparser.commands.dependency_resolver import DependencyResolver
from regparser.history import annual
from regparser.notice import preprocessors


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('year', type=int)
def fetch_annual_edition(cfr_title, cfr_part, year):
    """Download an annual edition of a regulation"""
    volume = annual.find_volume(year, cfr_title, cfr_part)
    xml = volume.find_part_xml(cfr_part)
    for preprocessor in preprocessors.ALL:
        preprocessor().transform(xml)
    eregs_index.AnnualEntry(cfr_title, cfr_part, year).write(xml)


class AnnualEditionResolver(DependencyResolver):
    PATH_PARTS = eregs_index.AnnualEntry.PREFIX + (
        '(?P<cfr_title>\d+)',
        '(?P<cfr_part>\d+)',
        '(?P<year>\d{4})')

    def resolution(self):
        args = [self.match.group('cfr_title'), self.match.group('cfr_part'),
                self.match.group('year')]
        return fetch_annual_edition.main(args, standalone_mode=False)
