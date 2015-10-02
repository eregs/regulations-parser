from importlib import import_module
import pkgutil

import click

from regparser import commands

try:
    import requests_cache   # @todo - replace with cache control
    requests_cache.install_cache('fr_cache')
except ImportError:
    # If the cache library isn't present, do nothing -- we'll just make full
    # HTTP requests rather than looking it up from the cache
    pass


@click.group()
def cli():
    pass


for _, command_name, _ in pkgutil.iter_modules(commands.__path__):
    module = import_module('regparser.commands.{}'.format(command_name))
    command = getattr(module, command_name)
    cli.add_command(command)


if __name__ == '__main__':
    cli()
