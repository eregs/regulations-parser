import logging

import click

logger = logging.getLogger(__name__)


@click.command()
@click.option('--markers', '-m', required=True)
def derive_depths(marker_string):
    return marker_string
