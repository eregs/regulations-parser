import logging

import click

from regparser.builder import LayerCacheAggregator, tree_and_builder
from regparser.diff.tree import changes_between
from regparser.tree.struct import FrozenNode


logger = logging.getLogger('build_from')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def gen_diffs(reg_tree, builder, layer_cache):
    """ Generate all the diffs for the given regulation. Broken out into
        separate function to assist with profiling so it's easier to determine
        which parts of the parser take the most time """
    doc_number, checkpointer = builder.doc_number, builder.checkpointer
    all_versions = {doc_number: FrozenNode.from_node(reg_tree)}

    for last_notice, old, new_tree, notices in builder.revision_generator(
            reg_tree):
        version = last_notice['document_number']
        logger.info("Version %s", version)
        all_versions[version] = FrozenNode.from_node(new_tree)
        builder.doc_number = version
        builder.write_regulation(new_tree)
        layer_cache.invalidate_by_notice(last_notice)
        builder.gen_and_write_layers(new_tree, layer_cache, notices)
        layer_cache.replace_using(new_tree)
        del last_notice, old, new_tree, notices     # free some memory

    label_id = reg_tree.label_id()
    writer = builder.writer
    del reg_tree, layer_cache, builder  # free some memory

    # now build diffs - include "empty" diffs comparing a version to itself
    for lhs_version, lhs_tree in all_versions.iteritems():
        for rhs_version, rhs_tree in all_versions.iteritems():
            changes = checkpointer.checkpoint(
                "-".join(["diff", lhs_version, rhs_version]),
                lambda: dict(changes_between(lhs_tree, rhs_tree)))
            writer.diff(
                label_id, lhs_version, rhs_version
            ).write(changes)


@click.command()
@click.argument('filename',
                type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument('title', type=int)
@click.option('--generate-diffs/--no-generate-diffs', default=True)
@click.option('--checkpoint', help='Directory to save checkpoint data',
              type=click.Path(file_okay=False, readable=True, writable=True))
@click.option('--version-identifier',
              help=('Do not try to derive the version information. (Only use '
                    'if the regulation has no electronic final rules on '
                    'federalregister.gov, i.e. has not changed since before '
                    '~2000)'))
# @profile
def build_from(filename, title, generate_diffs, checkpoint,
               version_identifier):
    """Build all data from provided xml. Reads the provided file and builds
    all versions of the regulation, its layers, etc. that follow.

    \b
    FILENAME: XML file containing the regulation
    TITLE: CFR title
    """
    #   First, the regulation tree
    reg_tree, builder = tree_and_builder(filename, title, checkpoint,
                                         version_identifier)
    builder.write_notices()

    #   Always do at least the first reg
    logger.info("Version %s", builder.doc_number)
    builder.write_regulation(reg_tree)
    layer_cache = LayerCacheAggregator()

    builder.gen_and_write_layers(reg_tree, layer_cache)
    layer_cache.replace_using(reg_tree)

    if generate_diffs:
        gen_diffs(reg_tree, builder, layer_cache)
