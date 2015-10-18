import click

from regparser import eregs_index
from regparser.diff.tree import changes_between


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def diffs(cfr_title, cfr_part):
    """Construct diffs between known trees."""
    tree_dir = eregs_index.FrozenTreeEntry(cfr_title, cfr_part)
    diff_dir = eregs_index.DiffEntry(cfr_title, cfr_part)
    pairs = [(lhs, rhs) for lhs in tree_dir for rhs in tree_dir]
    deps = eregs_index.DependencyGraph()
    for lhs_id, rhs_id in pairs:
        deps.add(diff_dir / lhs_id / rhs_id, tree_dir / lhs_id)
        deps.add(diff_dir / lhs_id / rhs_id, tree_dir / rhs_id)

    trees = {}
    for lhs_id, rhs_id in pairs:
        entry = diff_dir / lhs_id / rhs_id
        deps.validate_for(entry)
        if deps.is_stale(entry):
            if lhs_id not in trees:
                trees[lhs_id] = (tree_dir / lhs_id).read()
            if rhs_id not in trees:
                trees[rhs_id] = (tree_dir / rhs_id).read()

            entry.write(dict(changes_between(trees[lhs_id], trees[rhs_id])))
