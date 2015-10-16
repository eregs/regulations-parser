from unittest import TestCase

from click.testing import CliRunner

from regparser import eregs_index
from regparser.commands import fill_with_rules


class CommandsFillWithRulesTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_dependencies(self):
        """Expect nonexistent trees to depend on their predecessor, associated
        rule changes and version files. Shouldn't add dependencies for the
        first version, if missing"""
        with self.cli.isolated_filesystem():
            existing_trees = ['222', '555']
            version_ids = ['111', '222', '333', '444', '555', '666']
            deps = fill_with_rules.dependencies(
                existing_trees, version_ids, '12', '1000')
            paths = {
                version_id: deps.path_str('tree', '12', '1000', version_id)
                for version_id in version_ids}
            # First is skipped, as we can't build it from a rule
            self.assertNotIn(paths['111'], deps.graph)
            # Second can also be skipped as a tree already exists
            self.assertNotIn(paths['222'], deps.graph)
            # Third relies on the associated versions and the second tree
            self.assertEqual(
                deps.graph[paths['333']],
                set([paths['222'], deps.path_str('rule_changes', '333'),
                     deps.path_str('version', '12', '1000', '333')]))
            # Fourth relies on the third, even though it's not been built
            self.assertEqual(
                deps.graph[paths['444']],
                set([paths['333'], deps.path_str('rule_changes', '444'),
                     deps.path_str('version', '12', '1000', '444')]))
            # Fifth can be skipped as the tree already exists
            self.assertNotIn(paths['555'], deps.graph)
            # Six relies on the fifth
            self.assertEqual(
                deps.graph[paths['666']],
                set([paths['555'], deps.path_str('rule_changes', '666'),
                     deps.path_str('version', '12', '1000', '666')]))

    def test_derived_from_rules(self):
        """Should filter a set of version ids to only those with a dependency
        on changes derived from a rule"""
        with self.cli.isolated_filesystem():
            deps = eregs_index.DependencyGraph()
            deps.add(('tree', '12', '1000', '111'),
                     ('annual', '12', '1000', '2001'))
            deps.add(('tree', '12', '1000', '222'), ('rule_changes', '222'))
            deps.add(('tree', '12', '1000', '333'), ('rule_changes', '333'))
            deps.add(('tree', '12', '1000', '333'),
                     ('version', '12', '1000', '333'))
            derived = fill_with_rules.derived_from_rules(
                ['111', '222', '333', '444'], deps, '12', '1000')
            self.assertEqual(derived, ['222', '333'])
