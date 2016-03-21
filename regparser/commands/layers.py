import click
import logging

from regparser.index import dependency, entry
from regparser.plugins import classes_by_shorthand
import settings


LAYER_CLASSES = {
    doc_type: classes_by_shorthand(class_string_list)
    for doc_type, class_string_list in settings.LAYERS.items()}
# Also add in the "ALL" layers
for doc_type in LAYER_CLASSES:
    for layer_name, cls in LAYER_CLASSES['ALL'].items():
        LAYER_CLASSES[doc_type][layer_name] = cls
logger = logging.getLogger(__name__)


def stale_cfr_layers(version_entry):
    """Return the name of CFR layer dependencies which are now stale"""
    deps = dependency.Graph()
    tree_entry = entry.Tree(*version_entry.path)
    layer_dir = entry.Layer.cfr(*version_entry.path)
    for layer_name in LAYER_CLASSES['cfr']:
        # Layers depend on their associated tree
        deps.add(layer_dir / layer_name, tree_entry)
    # Meta layer also depends on the version info
    deps.add(layer_dir / 'meta', version_entry)

    for layer_name in LAYER_CLASSES['cfr']:
        layer_entry = layer_dir / layer_name
        deps.validate_for(layer_entry)
        if deps.is_stale(layer_entry):
            yield layer_name


def process_cfr_layers(stale_names, cfr_title, version_entry):
    """Build all of the stale layers for this version, writing them into the
    index. Assumes all dependencies have already been checked"""
    tree = entry.Tree(*version_entry.path).read()
    version = version_entry.read()
    layer_dir = entry.Layer.cfr(*version_entry.path)
    for layer_name in stale_names:
        layer_json = LAYER_CLASSES['cfr'][layer_name](
            tree, cfr_title=cfr_title, version=version).build()
        (layer_dir / layer_name).write(layer_json)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
# @todo - allow layers to be passed as a parameter
def layers(cfr_title, cfr_part):
    """Build all layers for all known versions."""
    logger.info("Build layers - %s CFR %s", cfr_title, cfr_part)
    tree_dir = entry.Tree(cfr_title, cfr_part)

    for version_id in tree_dir:
        version_entry = entry.Version(cfr_title, cfr_part, version_id)
        stale = stale_cfr_layers(version_entry)
        if stale:
            process_cfr_layers(stale, cfr_title, version_entry)
