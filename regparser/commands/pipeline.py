import click

from regparser.commands.annual_editions import annual_editions
from regparser.commands.annual_version import annual_version
from regparser.commands.diffs import diffs
from regparser.commands.fill_with_rules import fill_with_rules
from regparser.commands.layers import layers
from regparser.commands.versions import versions
from regparser.commands.write_to import write_to


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('output', envvar='EREGS_OUTPUT_DIR')
@click.option('--only-latest', is_flag=True, default=False,
              help="Don't derive history; use the latest annual edition")
@click.pass_context
def pipeline(ctx, cfr_title, cfr_part, output, only_latest):
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
    if only_latest:
        ctx.invoke(annual_version, **params)
    else:
        ctx.invoke(versions, **params)
        ctx.invoke(annual_editions, **params)
        ctx.invoke(fill_with_rules, **params)
    ctx.invoke(layers, **params)
    ctx.invoke(diffs, **params)
    ctx.invoke(write_to, output=output, **params)
