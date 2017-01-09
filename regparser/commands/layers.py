import logging

import click
from stevedore.extension import ExtensionManager

from regparser.commands import utils
from regparser.index import dependency, entry

logger = logging.getLogger(__name__)


def _init_classes():
    """Avoid leaking state variables by wrapping `LAYER_CLASSES` construction
    in a function"""
    classes = {}
    for doc_type in ('cfr', 'preamble'):    # @todo - make this dynamic
        namespace = 'eregs_ns.parser.layer.{0}'.format(doc_type)
        classes[doc_type] = {
            extension.name: extension.plugin
            for extension in ExtensionManager(namespace)
        }

    # For backwards compatibility. @todo - remove in later release
    old_namespace = 'eregs_ns.parser.layers'
    classes['cfr'].update({
        extension.plugin.shorthand: extension.plugin
        for extension in ExtensionManager(old_namespace)
    })
    return classes


LAYER_CLASSES = _init_classes()


def stale_layers(doc_entry, doc_type):
    """Return the name of layer dependencies which are now stale. Limit to a
    particular doc_type"""
    deps = dependency.Graph()
    layer_dir = entry.Layer(doc_type, *doc_entry.path)
    for layer_name in LAYER_CLASSES[doc_type]:
        # Layers depend on their associated tree
        deps.add(layer_dir / layer_name, doc_entry)
    if doc_type == 'cfr':
        # Meta layer also depends on the version info
        deps.add(layer_dir / 'meta', entry.Version(*doc_entry.path))

    stale = []
    for layer_name in LAYER_CLASSES[doc_type]:
        layer_entry = layer_dir / layer_name
        deps.validate_for(layer_entry)
        if deps.is_stale(layer_entry):
            stale.append(layer_name)
    return stale


def process_cfr_layers(stale_names, cfr_title, version_entry):
    """Build all of the stale layers for this version, writing them into the
    index. Assumes all dependencies have already been checked"""
    tree = entry.Tree(*version_entry.path).read()
    version = version_entry.read()
    layer_dir = entry.Layer.cfr(*version_entry.path)
    for layer_name in stale_names:
        layer_json = LAYER_CLASSES['cfr'][layer_name](
            tree, cfr_title=int(cfr_title), version=version).build()
        (layer_dir / layer_name).write(layer_json)


def process_preamble_layers(stale_names, preamble_entry):
    """Build all of the stale layers for this preamble, writing them into the
    index. Assumes all dependencies have already been checked"""
    tree = preamble_entry.read()
    layer_dir = entry.Layer.preamble(*preamble_entry.path)
    for layer_name in stale_names:
        layer_json = LAYER_CLASSES['preamble'][layer_name](tree).build()
        (layer_dir / layer_name).write(layer_json)


@click.command()
@click.option('--cfr_title', type=int, help="Limit to one CFR title")
@click.option('--cfr_part', type=int, help="Limit to one CFR part")
# @todo - allow layers to be passed as a parameter
def layers(cfr_title, cfr_part):
    """Build all layers for all known versions."""
    logger.info("Build layers - %s CFR %s", cfr_title, cfr_part)

    for tree_entry in utils.relevant_paths(entry.Tree(), cfr_title, cfr_part):
        tree_title, tree_part, version_id = tree_entry.path
        version_entry = entry.Version(tree_title, tree_part, version_id)
        stale = stale_layers(tree_entry, 'cfr')
        if stale:
            process_cfr_layers(stale, tree_title, version_entry)

    if cfr_title is None and cfr_part is None:
        for preamble_entry in entry.Preamble().sub_entries():
            stale = stale_layers(preamble_entry, 'preamble')
            if stale:
                process_preamble_layers(stale, preamble_entry)
