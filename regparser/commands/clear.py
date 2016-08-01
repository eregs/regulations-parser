import os
import shutil

import click
from django.conf import settings


@click.command()
@click.argument('path', nargs=-1)
def clear(path):
    """Delete intermediate and cache data. Only PATH arguments are cleared
    unless no arguments are present, then everything is wiped.

    \b
    $ eregs clear                   # clears everything
    $ eregs clear diff/27 trees     # deletes all cached trees and all CFR
                                    # title 27 diffs
    """
    if not path:
        path = ['']
    paths = [os.path.join(settings.EREGS_INDEX_ROOT, p) for p in path]
    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)
        else:
            click.echo("Warning: path does not exist: " + path)
