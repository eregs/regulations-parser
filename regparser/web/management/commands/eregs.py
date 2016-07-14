import logging
import os
import sys

import click
from djclick.adapter import BaseRegistrator, DjangoCommandMixin
import coloredlogs
import ipdb

from regparser.commands.retry import RetryingCommand
from regparser.index import http_cache


DEFAULT_LOG_FORMAT = "%(asctime)s %(name)-40s %(message)s"


class DjangoCommandRegistrator(BaseRegistrator):
    """Class which registers a command with Django. Uses the base classes
    provided by djclick"""
    cls = type('RetryDjangoCommand', (DjangoCommandMixin, RetryingCommand), {})


@DjangoCommandRegistrator()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    log_level = logging.INFO
    http_cache.install()
    if debug:
        log_level = logging.DEBUG
        sys.excepthook = lambda t, v, tb: ipdb.post_mortem(tb)
    coloredlogs.install(
        level=log_level,
        fmt=os.getenv("COLOREDLOGS_LOG_FORMAT", DEFAULT_LOG_FORMAT))
