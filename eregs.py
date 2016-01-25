import logging
from importlib import import_module
import pkgutil
import sys

import coloredlogs
import click
import ipdb
import requests_cache   # @todo - replace with cache control

from regparser import commands
from regparser.commands.dependency_resolver import DependencyResolver
from regparser.index import dependency


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    log_level = logging.INFO
    requests_cache.install_cache('fr_cache', expire_after=60*60*24*3)  # 3 days
    if debug:
        log_level = logging.DEBUG
        sys.excepthook = lambda t, v, tb: ipdb.post_mortem(tb)
    coloredlogs.install(level=log_level, fmt="%(levelname)s %(message)s")


for _, command_name, _ in pkgutil.iter_modules(commands.__path__):
    module = import_module('regparser.commands.{}'.format(command_name))
    if hasattr(module, command_name):
        subcommand = getattr(module, command_name)
        cli.add_command(subcommand)


def main(prev_dependency=None):
    """Wrapper around cli(), providing exception handling for dependency
    errors. When a dependency is missing, this will try to resolve that
    dependency and then retry running cli(). When retrying, the
    `prev_dependency` parameter indirectly tells us if we've progressed, due
    to the dependency changing"""
    try:
        cli()
    except dependency.Missing, e:
        resolvers = [resolver(e.dependency)
                     for resolver in DependencyResolver.__subclasses__()]
        resolvers = [r for r in resolvers if r.has_resolution()]
        if e.dependency == prev_dependency or len(resolvers) != 1:
            raise e
        else:
            click.echo("Attempting to resolve dependency: " + e.dependency)
            resolvers[0].resolution()
            main(e.dependency)


if __name__ == '__main__':
    main()
