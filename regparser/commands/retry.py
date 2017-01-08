import logging
import pkgutil
from collections import namedtuple
from copy import deepcopy
from importlib import import_module

import click
import pyparsing

from regparser import commands
from regparser.commands.dependency_resolver import DependencyResolver
from regparser.index import dependency

logger = logging.getLogger(__name__)

SubCommand = namedtuple('SubCommand', ['name', 'fn'])


def sub_commands():
    """Walk through the regparser.commands module looking for the presence of
    sub-commands"""
    sub_cmds = []
    for _, command_name, _ in pkgutil.iter_modules(commands.__path__):
        # Note - this import will also discover DependencyResolvers
        module = import_module('regparser.commands.{0}'.format(command_name))
        if hasattr(module, command_name):
            sub_cmds.append(
                SubCommand(command_name, getattr(module, command_name)))
    return sub_cmds


class RetryingCommand(click.MultiCommand):
    """Executes sub commands. If they fail due to a missing dependency,
    attempt to resolve then retry."""

    def list_commands(self, ctx):
        return [c.name for c in sub_commands()]

    def get_command(self, ctx, name):
        for command in sub_commands():
            if command.name == name:
                return command.fn

    def invoke(self, ctx):
        run_or_resolve(
            # deepcopy as invoke mutates the ctx
            lambda: super(RetryingCommand, self).invoke(deepcopy(ctx)))


def run_or_resolve(cmd, prev_dependency=None):
    """Wrapper around a click command or group, providing exception handling for
    dependency errors. When a dependency is missing, this will try to resolve
    that dependency and then retry running cli(). When retrying, the
    `prev_dependency` parameter indirectly tells us if we've progressed, due
    to the dependency changing"""
    try:
        cmd()
    except dependency.Missing as e:
        sub_commands()      # hack - creates DependencyResolver subclasses
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
