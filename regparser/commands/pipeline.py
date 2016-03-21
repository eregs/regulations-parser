import click

from regparser.commands.annual_editions import annual_editions
from regparser.commands.current_version import current_version
from regparser.commands.diffs import diffs
from regparser.commands.fill_with_rules import fill_with_rules
from regparser.commands.layers import layers
from regparser.commands.sxs_layers import sxs_layers
from regparser.commands.sync_xml import sync_xml
from regparser.commands.versions import versions
from regparser.commands.write_to import write_to


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('output')
@click.option('--only-latest', is_flag=True, default=False,
              help="Don't derive history; use the latest annual edition")
@click.option('--xml-ttl', type=int, default=60*60,
              help='Time to cache XML downloads, in seconds')
@click.pass_context
def pipeline(ctx, cfr_title, cfr_part, output, only_latest, xml_ttl):
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
    ctx.invoke(sync_xml, xml_ttl=xml_ttl)
    if only_latest:
        ctx.invoke(current_version, **params)
    else:
        ctx.invoke(versions, **params)
        ctx.invoke(annual_editions, **params)
        ctx.invoke(fill_with_rules, **params)
    ctx.invoke(layers, **params)
    # sxs_layers is required until we stop using SxS data for version info
    ctx.invoke(sxs_layers, **params)
    ctx.invoke(diffs, **params)
    ctx.invoke(write_to, output=output, **params)
