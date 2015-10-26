import click

from regparser import eregs_index
from regparser.api_writer import Client


def write_trees(client, cfr_title, cfr_part):
    tree_dir = eregs_index.TreeEntry(cfr_title, cfr_part)
    for version_id in eregs_index.VersionEntry(cfr_title, cfr_part):
        if version_id in tree_dir:
            click.echo("Writing tree " + version_id)
            tree = (tree_dir / version_id).read()
            client.regulation(cfr_part, version_id).write(tree)


def write_layers(client, cfr_title, cfr_part):
    for version_id in eregs_index.VersionEntry(cfr_title, cfr_part):
        layer_dir = eregs_index.LayerEntry(cfr_title, cfr_part, version_id)
        for layer_name in layer_dir:
            click.echo("Writing layer {}@{}".format(layer_name, version_id))
            layer = (layer_dir / layer_name).read()
            client.layer(layer_name, cfr_part, version_id).write(layer)


def write_notices(client, cfr_title, cfr_part):
    sxs_dir = eregs_index.SxSEntry()
    for version_id in eregs_index.VersionEntry(cfr_title, cfr_part):
        if version_id in sxs_dir:
            click.echo("Writing notice " + version_id)
            tree = (sxs_dir / version_id).read()
            client.notice(version_id).write(tree)


def write_diffs(client, cfr_title, cfr_part):
    diff_dir = eregs_index.DiffEntry(cfr_title, cfr_part)
    version_ids = list(eregs_index.VersionEntry(cfr_title, cfr_part))
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
    """TODO"""
    client = Client(output)
    cfr_part = str(cfr_part)
    write_trees(client, cfr_title, cfr_part)
    write_layers(client, cfr_title, cfr_part)
    write_notices(client, cfr_title, cfr_part)
    write_diffs(client, cfr_title, cfr_part)
