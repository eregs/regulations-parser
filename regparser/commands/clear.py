import os

import click
from django.conf import settings

from regparser.index.http_cache import http_client
from regparser.web.index.models import DependencyNode


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
    if path:
        paths = [os.path.join(settings.EREGS_INDEX_ROOT, p) for p in path]

        # Deleting cascades
        DependencyNode.objects.filter(pk__in=paths).delete()
        for path in paths:
            DependencyNode.objects.filter(pk__startswith=path).delete()
    else:
        DependencyNode.objects.all().delete()

    http_client().cache.clear()
