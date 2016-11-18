import click

from regparser.commands.dependency_resolver import DependencyResolver
from regparser.history import annual
from regparser.index import entry


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('year', type=int)
def fetch_annual_edition(cfr_title, cfr_part, year):
    """Download an annual edition of a regulation"""
    volume = annual.find_volume(year, cfr_title, cfr_part)
    xml = volume.find_part_xml(cfr_part).preprocess()
    annual_entry = entry.Annual(cfr_title, cfr_part, year)
    annual_entry.write(xml)


class AnnualEditionResolver(DependencyResolver):
    PATH_PARTS = (
        entry.Annual.PREFIX,
        r'(?P<cfr_title>\d+)',
        r'(?P<cfr_part>\d+)',
        r'(?P<year>\d{4})')

    def resolution(self):
        args = [self.match.group('cfr_title'), self.match.group('cfr_part'),
                self.match.group('year')]
        return fetch_annual_edition.main(args, standalone_mode=False)
