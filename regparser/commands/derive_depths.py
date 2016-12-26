import logging

import click

logger = logging.getLogger(__name__)


@click.command()
@click.argument('markers', type=click.STRING, required=True)
def derive_depths(marker_string):
    """
    Infer an outline's structure.
    Return a list of outline depths for a given list of comma-separated markers.
    """
    return marker_string

