import click

from regparser import eregs_index
from regparser.builder import merge_changes
from regparser.notice.compiler import compile_regulation


def dependencies(tree_path, version_ids, cfr_title, cfr_part):
    """Set up the dependency graph for this regulation. First calculates
    "gaps" -- versions for which there is no existing tree. In this
    calculation, we ignore the first version, as we won't be able to build
    anything for it. Add dependencies for any gaps, tying the output tree to
    the preceding tree, the version info and the parsed rule"""
    existing_ids = set(tree_path)
    gaps = [(prev, curr) for prev, curr in zip(version_ids, version_ids[1:])
            if curr not in existing_ids]

    deps = eregs_index.DependencyGraph()
    for prev, curr in gaps:
        curr_tuple = ('tree', cfr_title, cfr_part, curr)
        deps.add(curr_tuple, ('tree', cfr_title, cfr_part, prev))
        deps.add(curr_tuple, ('rule_changes', curr))
        deps.add(curr_tuple, ('version', cfr_title, cfr_part, curr))
    return deps


def derived_from_rules(version_ids, deps, cfr_title, cfr_part):
    """We only want to process trees which are created by parsing rules. To do
    that, we'll filter by those trees which have a dependency on a parsed
    rule"""
    rule_versions = []
    for version_id in version_ids:
        path = deps.path_str('tree', cfr_title, cfr_part, version_id)
        rule_change = deps.path_str('rule_changes', version_id)
        if rule_change in deps.graph.get(path, []):
            rule_versions.append(version_id)
    return rule_versions


def process(tree_path, previous, version_id):
    """Build and write a tree by combining the preceding tree with changes
    present in the associated rule"""
    prev_tree = tree_path.read(previous)
    notice = eregs_index.Path('rule_changes').read_json(version_id)
    changes = merge_changes(version_id, notice.get('changes', {}))
    new_tree = compile_regulation(prev_tree, changes)
    tree_path.write(version_id, new_tree)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def fill_with_rules(cfr_title, cfr_part):
    """Fill in missing trees using data from rules. When a regulation tree
    cannot be derived through annual editions, it must be built by parsing the
    changes in final rules. This command builds those missing trees"""
    tree_path = eregs_index.TreePath(cfr_title, cfr_part)
    version_ids = [v.identifier
                   for v in eregs_index.VersionPath(cfr_title, cfr_part)]
    deps = dependencies(tree_path, version_ids, cfr_title, cfr_part)

    preceeded_by = dict(zip(version_ids[1:], version_ids))
    derived = derived_from_rules(version_ids, deps, cfr_title, cfr_part)
    for version_id in derived:
        deps.validate_for('tree', cfr_title, cfr_part, version_id)
        if deps.is_stale('tree', cfr_title, cfr_part, version_id):
            process(tree_path, preceeded_by[version_id], version_id)
