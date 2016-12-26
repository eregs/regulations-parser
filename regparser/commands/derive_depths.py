import logging

import click

logger = logging.getLogger(__name__)


@click.command()
@click.argument('markers', type=click.STRING, required=True)
def derive_depths(markers) -> None:
    """
    Infer an outline's structure.
    Return a list of outline depths for a given list of comma-separated markers.
    """
    print(markers)


if __name__ == '__main__':
    """Enable running this command directly. E.g.,
    `$ python regparser/commands/derive_depths.py`. This can save 1.5 seconds or
    more of startup time.
    """
    derive_depths()
