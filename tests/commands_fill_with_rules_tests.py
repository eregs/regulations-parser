from datetime import date
from unittest import TestCase

from click.testing import CliRunner
from mock import patch
import pytest
import six

from regparser.commands import fill_with_rules
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.tree.struct import Node


@pytest.mark.django_db
class CommandsFillWithRulesTests(TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_dependencies(self):
        """Expect nonexistent trees to depend on their predecessor, associated
        rule changes and version files. Shouldn't add dependencies for the
        first version, if missing"""
        with self.cli.isolated_filesystem():
            versions = [Version(str(i)*3, date(2001, i, i), date(2002, i, i))
                        for i in range(1, 7)]
            parents = Version.parents_of(versions)
            tree_dir = entry.Tree('12', '1000')
            notice_dir = entry.Notice()
            vers_dir = entry.Version('12', '1000')
            # Existing trees
            (tree_dir / '222').write(Node())
            (tree_dir / '555').write(Node())

            deps = fill_with_rules.dependencies(
                tree_dir, vers_dir, list(zip(versions, parents)))

            # First is skipped, as we can't build it from a rule
            self.assertNotIn(str(tree_dir / '111'), deps)
            # Second can also be skipped as a tree already exists
            self.assertEqual(deps.dependencies(str(tree_dir / '222')), [])
            # Third relies on the associated versions and the second tree
            six.assertCountEqual(
                self,
                deps.dependencies(str(tree_dir / '333')),
                [str(tree_dir / '222'), str(notice_dir / '333'),
                 str(vers_dir / '333')])
            # Fourth relies on the third, even though it's not been built
            six.assertCountEqual(
                self,
                deps.dependencies(str(tree_dir / '444')),
                [str(tree_dir / '333'), str(notice_dir / '444'),
                 str(vers_dir / '444')])
            # Fifth can be skipped as the tree already exists
            self.assertEqual(deps.dependencies(str(tree_dir / '555')), [])
            # Six relies on the fifth
            six.assertCountEqual(
                self,
                deps.dependencies(str(tree_dir / '666')),
                [str(tree_dir / '555'), str(notice_dir / '666'),
                 str(vers_dir / '666')])

    def test_is_derived(self):
        """Should filter version ids to only those with a dependency on
        changes derived from a rule"""
        with self.cli.isolated_filesystem():
            tree_dir = entry.Tree('12', '1000')

            deps = dependency.Graph()
            deps.add(tree_dir / 111, entry.Annual(12, 1000, 2001))
            deps.add(tree_dir / 222, entry.Notice(222))
            deps.add(tree_dir / 333, entry.Notice(333))
            deps.add(tree_dir / 333, entry.Version(333))
            self.assertFalse(fill_with_rules.is_derived('111', deps, tree_dir))
            self.assertTrue(fill_with_rules.is_derived('222', deps, tree_dir))
            self.assertTrue(fill_with_rules.is_derived('333', deps, tree_dir))
            self.assertFalse(fill_with_rules.is_derived('444', deps, tree_dir))

    @patch('regparser.commands.fill_with_rules.compile_regulation')
    @patch('regparser.commands.fill_with_rules.entry.Notice')
    def test_process(self, Notice, compile_regulation):
        """Verify that the correct changes are found"""
        compile_regulation.return_value = Node()
        # entry.Notice('new').read().amendments
        Notice.return_value.read.return_value.amendments = [
            {"instruction": "Something something",
             "cfr_part": "1000",
             "authority": "USC Numbers"},
            {"instruction": "More things",
             "cfr_part": "1000",
             "changes": [["1000-2-b", ["2b changes"]],
                         ["1000-2-c", ["2c changes"]]]},
            {"instruction": "Yet more changes",
             "cfr_part": "1000",
             "changes": [["1000-4-a", ["4a changes"]]]}
        ]
        with self.cli.isolated_filesystem():
            tree_dir = entry.Tree('12', '1000')
            (tree_dir / 'old').write(Node())
            entry.Entry('notice_xml', 'new').write(b'')
            fill_with_rules.process(tree_dir, 'old', 'new')
            changes = dict(compile_regulation.call_args[0][1])
            self.assertEqual(changes, {
                "1000-2-b": ["2b changes"], "1000-2-c": ["2c changes"],
                "1000-4-a": ["4a changes"]})


def test_drop_initial_orphan_versions():
    version_list = [Version(letter, None, None) for letter in 'abcdef']
    version_pairs = list(zip(version_list, [None] + version_list[1:]))
    existing = {'c', 'e'}

    result = fill_with_rules.drop_initial_orphans(version_pairs, existing)
    result = [pair[0].identifier for pair in result]

    assert result == ['c', 'd', 'e', 'f']
