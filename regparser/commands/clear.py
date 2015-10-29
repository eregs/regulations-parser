import os
import shutil

import click

from regparser import eregs_index


SQLITE_CACHE = 'fr_cache.sqlite'


@click.command()
@click.argument('path', nargs=-1)
@click.option('--http-cache/--no-http-cache', default=False,
              help="Clear HTTP request (FR, GPO, etc.). Defaults false")
def clear(path, http_cache):
    """Delete intermediate data. Only PATH arguments are cleared unless no
    arguments are present, then everything is wiped.

    \b
    $ eregs clear                   # clears everything
    $ eregs clear diff/27 trees     # deletes all cached trees and all CFR
                                    # title 27 diffs
    """
    if not path:
        path = ['']
    paths = [os.path.join(eregs_index.ROOT, p) for p in path]
    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)
        else:
            click.echo("Warning: path does not exist: " + path)

    if http_cache and os.path.exists(SQLITE_CACHE):
        os.remove(SQLITE_CACHE)
