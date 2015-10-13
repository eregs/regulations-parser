import os
import shutil

import click

from regparser import eregs_index


@click.command()
def clear():
    """Delete all intermediate data. Generally not needed, but this is a
    simple method to start fresh regarding intermediate and cached data"""
    if os.path.exists(eregs_index.ROOT):
        shutil.rmtree(eregs_index.ROOT)
    if os.path.exists("fr_cache.sqlite"):
        os.remove("fr_cache.sqlite")
