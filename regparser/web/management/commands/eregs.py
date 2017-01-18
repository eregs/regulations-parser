import logging
import os
import sys

import click
import coloredlogs
import ipdb
from djclick.adapter import BaseRegistrator, DjangoCommandMixin

from regparser.commands.retry import RetryingCommand

DEFAULT_LOG_FORMAT = "%(asctime)s %(name)-40s %(message)s"


class DjangoCommandRegistrator(BaseRegistrator):
    """Class which registers a command with Django. Uses the base classes
    provided by djclick"""
    cls = type('RetryDjangoCommand', (DjangoCommandMixin, RetryingCommand), {})


@DjangoCommandRegistrator()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
        sys.excepthook = lambda t, v, tb: ipdb.post_mortem(tb)
    coloredlogs.install(
        level=log_level,
        fmt=os.getenv("COLOREDLOGS_LOG_FORMAT", DEFAULT_LOG_FORMAT))
