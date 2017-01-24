import logging
from collections import defaultdict

import click

from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.notice.compiler import compile_regulation

logger = logging.getLogger(__name__)


def drop_initial_orphans(versions_with_parents, existing):
    """We can only build a version if there's a complete tree before it to
    build from. As such, we need to drop any orphaned versions from the
    beginning of our list"""
    for idx, (version, _) in enumerate(versions_with_parents):
        if version.identifier in existing:
            return versions_with_parents[idx:]
        logger.warning("No previous annual edition to version %s; ignoring",
                       version.identifier)
    return []


def dependencies(tree_dir, version_dir, versions_with_parents):
    """Set up the dependency graph for this regulation. First calculates
    "gaps" -- versions for which there is no existing tree. In this
    calculation, we ignore the first version, as we won't be able to build
    anything for it. Add dependencies for any gaps, tying the output tree to
    the preceding tree, the version info and the parsed rule"""
    existing_tree_ids = {tree.path[-1] for tree in tree_dir.sub_entries()}
    version_pairs = drop_initial_orphans(
        versions_with_parents, existing_tree_ids)
    gaps = [(version, parent) for (version, parent) in version_pairs
            if version.identifier not in existing_tree_ids]

    deps = dependency.Graph()
    for version, parent in gaps:
        doc_number = version.identifier
        deps.add(tree_dir / doc_number, tree_dir / parent.identifier)
        deps.add(tree_dir / doc_number, entry.Notice(doc_number))
        deps.add(tree_dir / doc_number, version_dir / doc_number)
    return deps


def is_derived(version_id, deps, tree_dir):
    """We only want to process trees which are created by parsing rules. To do
    that, we'll filter by those trees which have a dependency on a parsed
    rule"""
    tree = str(tree_dir / version_id)
    notice = str(entry.Notice(version_id))
    return notice in deps.dependencies(tree)


def process(tree_path, previous, version_id):
    """Build and write a tree by combining the preceding tree with changes
    present in the associated rule"""
    prev_tree = (tree_path / previous).read()
    notice = entry.Notice(version_id).read()
    notice_changes = defaultdict(list)
    for amendment in notice.amendments:
        for label, change_list in amendment.get('changes', []):
            notice_changes[label].extend(change_list)
    new_tree = compile_regulation(prev_tree, notice_changes)
    (tree_path / version_id).write(new_tree)


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def fill_with_rules(cfr_title, cfr_part):
    """Fill in missing trees using data from rules. When a regulation tree
    cannot be derived through annual editions, it must be built by parsing the
    changes in final rules. This command builds those missing trees"""
    logger.info("Fill with rules - %s CFR %s", cfr_title, cfr_part)
    tree_dir = entry.Tree(cfr_title, cfr_part)
    version_dir = entry.Version(cfr_title, cfr_part)

    versions = [c.read() for c in version_dir.sub_entries()]
    versions_with_parents = list(zip(versions, Version.parents_of(versions)))
    deps = dependencies(tree_dir, version_dir, versions_with_parents)

    derived = [(version.identifier, parent.identifier)
               for version, parent in versions_with_parents
               if is_derived(version.identifier, deps, tree_dir) and parent]
    for version_id, parent_id in derived:
        deps.validate_for(tree_dir / version_id)
        if deps.is_stale(tree_dir / version_id):
            process(tree_dir, parent_id, version_id)
            deps.rebuild()
