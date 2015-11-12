import click

from regparser.commands.versions import versions
from regparser.commands.annual_editions import annual_editions
from regparser.commands.fill_with_rules import fill_with_rules
from regparser.commands.layers import layers
from regparser.commands.diffs import diffs
from regparser.commands.write_to import write_to
from regparser.commands.sync_xml import sync_xml


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('output')
@click.pass_context
def pipeline(ctx, cfr_title, cfr_part, output):
    """Full regulation parsing pipeline. Consists of retrieving and parsing
    annual edition, attempting to parse final rules in between, deriving
    layers and diffs, and writing them to disk or an API

    \b
    OUTPUT can be a
    * directory (if it does not exist, it will be created)
    * uri (the base url of an instance of regulations-core)
    * a directory prefixed with "git://". This will export to a git
      repository"""
    params = {'cfr_title': cfr_title, 'cfr_part': cfr_part}
    ctx.invoke(sync_xml)
    ctx.invoke(versions, **params)
    ctx.invoke(annual_editions, **params)
    ctx.invoke(fill_with_rules, **params)
    ctx.invoke(layers, **params)
    ctx.invoke(diffs, **params)
    ctx.forward(write_to)
