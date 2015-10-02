# @todo - this should be combined with build_from.py
import click

from regparser.builder import tree_and_builder
from regparser.notice.changes import node_to_dict, pretty_change
from regparser.tree.struct import find


@click.command()
@click.argument('node_label')
@click.argument('filename',
                type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument('title', type=int)
def watch_node(node_label, filename, title):
    """Follow changes to a particular label.

    \b
    NODE_LABEL: Label for the node you wish to watch. e.g. 1026-5-a
    FILENAME: XML file containing the regulation
    TITLE: Title number"""

    initial_tree, builder = tree_and_builder(filename, title)
    initial_node = find(initial_tree, node_label)
    if initial_node:
        click.echo("> " + builder.doc_number)
        click.echo("\t" + pretty_change(
            {'action': 'POST', 'node': node_to_dict(initial_node)}))

    # search for label
    for version, changes in builder.changes_in_sequence():
        if node_label in changes:
            click.echo("> " + version)
            for change in changes[node_label]:
                click.echo("\t" + pretty_change(change))
