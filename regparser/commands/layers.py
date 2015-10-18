import click

from regparser import eregs_index
from regparser.layer import ALL_LAYERS


def dependencies(tree_dir, layer_dir, version_dir):
    """Modify and return the dependency graph pertaining to layers"""
    deps = eregs_index.DependencyGraph()
    sxs_dir = eregs_index.SxSEntry()
    for version_id in tree_dir:
        for layer_name in ALL_LAYERS:
            # Layers depend on their associated tree
            deps.add(layer_dir / version_id / layer_name,
                     tree_dir / version_id)
        # Meta layer also depends on the version info
        deps.add(layer_dir / version_id / 'meta', version_dir / version_id)
        for document_number in sxs_source_names(version_dir, version_id):
            deps.add(layer_dir / version_id / 'analyses',
                     sxs_dir / document_number)
    return deps


def sxs_source_names(version_dir, stop_version):
    """The SxS layer relies on all of notices that came before a particular
    version"""
    for version_id in version_dir:
        if version_id in eregs_index.NoticeEntry():
            yield version_id
        if version_id == stop_version:
            break


def sxs_sources(version_dir, version_id):
    """Wrapper reading JSON for the sxs_source_names"""
    return [(eregs_index.SxSEntry() / doc_num).read()
            for doc_num in sxs_source_names(version_dir, version_id)]


def stale_layers(deps, layer_dir):
    """Return all of the layer dependencies which are now stale within
    layer_dir"""
    for layer_name in ALL_LAYERS:
        entry = layer_dir / layer_name
        deps.validate_for(entry)
        if deps.is_stale(entry):
            yield layer_name


def process_layers(stale, cfr_title, cfr_part, version, act_citation):
    """Build all of the stale layers for this version, writing them into the
    index. Assumes all dependencies have already been checked"""
    tree = eregs_index.TreeEntry(
        cfr_title, cfr_part, version.identifier).read()
    version_dir = eregs_index.VersionEntry(cfr_title, cfr_part)
    layer_dir = eregs_index.LayerEntry(cfr_title, cfr_part)
    for layer_name in stale:
        notices = []
        if layer_name == 'analyses':
            notices = sxs_sources(version_dir, version.identifier)
        layer_json = ALL_LAYERS[layer_name](
            tree, cfr_title, notices=notices, act_citation=act_citation,
            version=version).build()
        (layer_dir / version.identifier / layer_name).write(layer_json)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.option('--act_title', type=int, default=0,
              help=('Title of the act of congress providing authority for '
                    'this regulation'))
@click.option('--act_section', type=int, default=0,
              help=('Section of the act of congress providing authority for '
                    'this regulation'))
# @todo - allow layers to be passed as a parameter
def layers(cfr_title, cfr_part, act_title, act_section):
    """Build all layers for all known versions."""
    tree_dir = eregs_index.TreeEntry(cfr_title, cfr_part)
    layer_dir = eregs_index.LayerEntry(cfr_title, cfr_part)
    version_dir = eregs_index.VersionEntry(cfr_title, cfr_part)
    deps = dependencies(tree_dir, layer_dir, version_dir)

    for version_id in tree_dir:
        stale = list(stale_layers(deps, layer_dir / version_id))
        if stale:
            process_layers(
                stale, cfr_title, cfr_part,
                version=(version_dir / version_id).read(),
                act_citation=(act_title, act_section)
            )
