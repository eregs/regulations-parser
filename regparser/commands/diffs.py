import click
import logging

from regparser.diff.tree import changes_between
from regparser.index import dependency, entry

logger = logging.getLogger(__name__)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def diffs(cfr_title, cfr_part):
    """Construct diffs between known trees."""
    logger.info("Build diffs - %s Part %s", cfr_title, cfr_part)
    tree_dir = entry.FrozenTree(cfr_title, cfr_part)
    diff_dir = entry.Diff(cfr_title, cfr_part)
    pairs = [(lhs, rhs) for lhs in tree_dir for rhs in tree_dir]
    deps = dependency.Graph()
    for lhs_id, rhs_id in pairs:
        deps.add(diff_dir / lhs_id / rhs_id, tree_dir / lhs_id)
        deps.add(diff_dir / lhs_id / rhs_id, tree_dir / rhs_id)

    trees = {}
    for lhs_id, rhs_id in pairs:
        path = diff_dir / lhs_id / rhs_id
        deps.validate_for(path)
        if deps.is_stale(path):
            if lhs_id not in trees:
                trees[lhs_id] = (tree_dir / lhs_id).read()
            if rhs_id not in trees:
                trees[rhs_id] = (tree_dir / rhs_id).read()

            path.write(dict(changes_between(trees[lhs_id], trees[rhs_id])))
