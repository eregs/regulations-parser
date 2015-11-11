import click

from regparser.api_writer import Client
from regparser.index import entry


# The write process is split into a set of functions, each responsible for
# writing a particular type of entity

def write_trees(client, cfr_title, cfr_part):
    tree_dir = entry.Tree(cfr_title, cfr_part)
    for version_id in entry.Version(cfr_title, cfr_part):
        if version_id in tree_dir:
            click.echo("Writing tree " + version_id)
            tree = (tree_dir / version_id).read()
            client.regulation(cfr_part, version_id).write(tree)


def write_layers(client, cfr_title, cfr_part):
    for version_id in entry.Version(cfr_title, cfr_part):
        layer_dir = entry.Layer(cfr_title, cfr_part, version_id)
        for layer_name in layer_dir:
            click.echo("Writing layer {}@{}".format(layer_name, version_id))
            layer = (layer_dir / layer_name).read()
            client.layer(layer_name, cfr_part, version_id).write(layer)


def write_notices(client, cfr_title, cfr_part):
    sxs_dir = entry.SxS()
    for version_id in entry.Version(cfr_title, cfr_part):
        if version_id in sxs_dir:
            click.echo("Writing notice " + version_id)
            tree = (sxs_dir / version_id).read()
            client.notice(version_id).write(tree)


def write_diffs(client, cfr_title, cfr_part):
    diff_dir = entry.Diff(cfr_title, cfr_part)
    version_ids = list(entry.Version(cfr_title, cfr_part))
    for lhs_id in version_ids:
        container = diff_dir / lhs_id
        for rhs_id in version_ids:
            if rhs_id in container:
                click.echo("Writing diff {} to {}".format(lhs_id, rhs_id))
                diff = (container / rhs_id).read()
                client.diff(cfr_part, lhs_id, rhs_id).write(diff)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('output')
def write_to(cfr_title, cfr_part, output):
    """Export data. Sends all data in the index to an external source.

    \b
    OUTPUT can be a
    * directory (if it does not exist, it will be created)
    * uri (the base url of an instance of regulations-core)
    * a directory prefixed with "git://". This will export to a git
      repository"""
    client = Client(output)
    cfr_part = str(cfr_part)
    write_trees(client, cfr_title, cfr_part)
    write_layers(client, cfr_title, cfr_part)
    write_notices(client, cfr_title, cfr_part)
    write_diffs(client, cfr_title, cfr_part)
