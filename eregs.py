from copy import deepcopy
from collections import namedtuple
import logging
from importlib import import_module
import os
import pkgutil
import sys

import coloredlogs
import click
import ipdb
import pyparsing

from regparser import commands
from regparser.commands.dependency_resolver import DependencyResolver
from regparser.index import dependency, http_cache

logger = logging.getLogger(__name__)
DEFAULT_LOG_FORMAT = "%(asctime)s %(name)-40s %(message)s"

SubCommand = namedtuple('SubCommand', ['name', 'fn'])
sub_commands = []
for _, command_name, _ in pkgutil.iter_modules(commands.__path__):
    # Note - this import will also discover DependencyResolvers
    module = import_module('regparser.commands.{}'.format(command_name))
    if hasattr(module, command_name):
        sub_commands.append(
            SubCommand(command_name, getattr(module, command_name)))


class RetryingCommand(click.MultiCommand):
    """Executes sub commands. If they fail due to a missing dependency,
    attempt to resolve then retry."""

    def list_commands(self, ctx):
        return [c.name for c in sub_commands]

    def get_command(self, ctx, name):
        for command in sub_commands:
            if command.name == name:
                return command.fn

    def invoke(self, ctx):
        run_or_resolve(
            # deepcopy as invoke mutates the ctx
            lambda: super(RetryingCommand, self).invoke(deepcopy(ctx)))


@click.command(cls=RetryingCommand)
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


def run_or_resolve(cmd, prev_dependency=None):
    """Wrapper around a click command or group, providing exception handling for
    dependency errors. When a dependency is missing, this will try to resolve
    that dependency and then retry running cli(). When retrying, the
    `prev_dependency` parameter indirectly tells us if we've progressed, due
    to the dependency changing"""
    try:
        cmd()
    except dependency.Missing as e:
        resolvers = [resolver(e.dependency)
                     for resolver in DependencyResolver.__subclasses__()]
        resolvers = [r for r in resolvers if r.has_resolution()]
        if e.dependency == prev_dependency or len(resolvers) != 1:
            raise e
        else:
            logger.info("Attempting to resolve dependency: %s", e.dependency)
            resolvers[0].resolution()
            run_or_resolve(cmd, e.dependency)
    except pyparsing.ParseException as exc:
        logger.error(u"%s:\n'%s'", exc, exc.line)
        raise


if __name__ == '__main__':
    cli()
