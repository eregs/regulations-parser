import click

from regparser.index import dependency, entry
from regparser.plugins import classes_by_shorthand
import settings

ALL_LAYERS = classes_by_shorthand(settings.LAYERS)


def dependencies(tree_dir, layer_dir, version_dir):
    """Modify and return the dependency graph pertaining to layers"""
    deps = dependency.Graph()
    sxs_dir = entry.SxS()
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
        if version_id in entry.Notice():
            yield version_id
        if version_id == stop_version:
            break


def sxs_sources(version_dir, version_id):
    """Wrapper reading JSON for the sxs_source_names"""
    return [(entry.SxS() / doc_num).read()
            for doc_num in sxs_source_names(version_dir, version_id)]


def stale_layers(deps, layer_dir):
    """Return all of the layer dependencies which are now stale within
    layer_dir"""
    for layer_name in ALL_LAYERS:
        entry = layer_dir / layer_name
        deps.validate_for(entry)
        if deps.is_stale(entry):
            yield layer_name


def process_layers(stale, cfr_title, cfr_part, version):
    """Build all of the stale layers for this version, writing them into the
    index. Assumes all dependencies have already been checked"""
    tree = entry.Tree(cfr_title, cfr_part, version.identifier).read()
    version_dir = entry.Version(cfr_title, cfr_part)
    layer_dir = entry.Layer(cfr_title, cfr_part)
    for layer_name in stale:
        notices = []
        if layer_name == 'analyses':
            notices = sxs_sources(version_dir, version.identifier)
        layer_json = ALL_LAYERS[layer_name](
            tree, cfr_title, notices=notices, version=version).build()
        (layer_dir / version.identifier / layer_name).write(layer_json)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
# @todo - allow layers to be passed as a parameter
def layers(cfr_title, cfr_part):
    """Build all layers for all known versions."""
    tree_dir = entry.Tree(cfr_title, cfr_part)
    layer_dir = entry.Layer(cfr_title, cfr_part)
    version_dir = entry.Version(cfr_title, cfr_part)
    deps = dependencies(tree_dir, layer_dir, version_dir)

    for version_id in tree_dir:
        stale = list(stale_layers(deps, layer_dir / version_id))
        if stale:
            process_layers(
                stale, cfr_title, cfr_part,
                version=(version_dir / version_id).read()
            )
