import click
import logging

from regparser.api_writer import Client
from regparser.index import entry


logger = logging.getLogger(__name__)


def relevant_paths(root_dir, only_title, only_part):
    """We may want to filter the paths we search in to those relevant to a
    particular cfr title/part. Most index entries encode this as their first
    two path components"""
    title_dirs = [(root_dir / title) for title in root_dir
                  if not only_title or str(only_title) == title]
    part_dirs = [(title_dir / part)
                 for title_dir in title_dirs for part in title_dir
                 if not only_part or str(only_part) == part]
    return [(part_dir / child)
            for part_dir in part_dirs for child in part_dir]


def write_trees(client, only_title, only_part):
    for tree_entry in relevant_paths(entry.Tree(), only_title, only_part):
        cfr_title, cfr_part, version_id = tree_entry.path
        client.regulation(cfr_part, version_id).write(tree_entry.read())


def write_layers(client, only_title, only_part):
    for layer_dir in relevant_paths(entry.Layer.cfr(), only_title, only_part):
        doc_type, cfr_title, cfr_part, version_id = layer_dir.path
        for layer_name in layer_dir:
            layer = (layer_dir / layer_name).read()
            client.layer(layer_name, cfr_part, version_id).write(layer)


def write_notices(client, only_title, only_part):
    sxs_dir = entry.SxS()
    for version_id in sxs_dir:
        tree = (sxs_dir / version_id).read()
        title_match = not only_title or tree['cfr_title'] == only_title
        cfr_parts = map(str, tree['cfr_parts'])
        part_match = not only_part or str(only_part) in cfr_parts
        if title_match and part_match:
            client.notice(version_id).write(tree)


def write_diffs(client, only_title, only_part):
    for diff_dir in relevant_paths(entry.Diff(), only_title, only_part):
        cfr_title, cfr_part, lhs_id = diff_dir.path
        for rhs_id in diff_dir:
            diff = (diff_dir / rhs_id).read()
            client.diff(cfr_part, lhs_id, rhs_id).write(diff)


def write_preambles(client):
    for doc_id in entry.Preamble():
        preamble = entry.Preamble(doc_id).read()
        client.preamble(doc_id).write(preamble)


@click.command()
@click.argument('output')
@click.option('--cfr_title', type=int, help="Limit to one CFR title")
@click.option('--cfr_part', type=int, help="Limit to one CFR part")
def write_to(output, cfr_title, cfr_part):
    """Export data. Sends all data in the index to an external source.

    \b
    OUTPUT can be a
    * directory (if it does not exist, it will be created)
    * uri (the base url of an instance of regulations-core)
    * a directory prefixed with "git://". This will export to a git
      repository"""
    logger.info("Export output - %s CFR %s, Destination: %s",
                cfr_title, cfr_part, output)
    client = Client(output)
    write_trees(client, cfr_title, cfr_part)
    write_layers(client, cfr_title, cfr_part)
    write_notices(client, cfr_title, cfr_part)
    write_diffs(client, cfr_title, cfr_part)
    if cfr_title is None and cfr_part is None:
        write_preambles(client)
