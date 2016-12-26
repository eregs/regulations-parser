import logging
from regparser.tree.depth.derive import derive_depths

import click

logger = logging.getLogger(__name__)


@click.command()
@click.argument('markers', type=click.STRING, required=True)
def outline_depths(markers) -> None:
    """
    Infer an outline's structure.
    Return a list of outline depths for a given list of comma-separated markers.
    """
    depths = derive_depths(markers.split(','), [])
    solution = {tuple(a.depth for a in s) for s in depths}.pop()
    formatted_output = ','.join((str(a) for a in solution))

    print(formatted_output)


if __name__ == '__main__':
    """Enable running this command directly. E.g.,
    `$ python regparser/commands/outline_depths.py`. This can save 1.5 seconds or
    more of startup time.
    """
    outline_depths()
