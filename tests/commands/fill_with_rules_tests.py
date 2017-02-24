from datetime import date

import pytest
from mock import Mock

from regparser.commands import fill_with_rules
from regparser.index import dependency, entry
from regparser.tree.struct import Node
from regparser.web.index.models import CFRVersion


@pytest.mark.django_db
def test_dependencies():
    """Expect nonexistent trees to depend on their predecessor, associated
    rule changes and version files. Shouldn't add dependencies for the
    first version, if missing"""
    versions = [
        CFRVersion(identifier=str(i)*3, effective=date(2001, i, i))
        for i in range(1, 7)
    ]
    parents = CFRVersion.parents_of(versions)
    tree_dir = entry.Tree('12', '1000')
    notice_dir = entry.Notice()
    vers_dir = entry.Version('12', '1000')
    # Existing trees
    (tree_dir / '222').write(Node())
    (tree_dir / '555').write(Node())

    deps = fill_with_rules.dependencies(tree_dir, vers_dir,
                                        list(zip(versions, parents)))

    # First is skipped, as we can't build it from a rule
    assert str(tree_dir / '111') not in deps
    # Second can also be skipped as a tree already exists
    assert deps.dependencies(str(tree_dir / '222')) == []
    # Third relies on the associated versions and the second tree
    expected = {str(tree_dir / '222'), str(notice_dir / '333'),
                str(vers_dir / '333')}
    assert set(deps.dependencies(str(tree_dir / '333'))) == expected
    # Fourth relies on the third, even though it's not been built
    expected = {str(tree_dir / '333'), str(notice_dir / '444'),
                str(vers_dir / '444')}
    assert set(deps.dependencies(str(tree_dir / '444'))) == expected
    # Fifth can be skipped as the tree already exists
    assert deps.dependencies(str(tree_dir / '555')) == []
    # Six relies on the fifth
    expected = {str(tree_dir / '555'), str(notice_dir / '666'),
                str(vers_dir / '666')}
    assert set(deps.dependencies(str(tree_dir / '666'))) == expected


@pytest.mark.django_db
def test_is_derived():
    """Should filter version ids to only those with a dependency on
    changes derived from a rule"""
    tree_dir = entry.Tree('12', '1000')

    deps = dependency.Graph()
    deps.add(tree_dir / 111, entry.Annual(12, 1000, 2001))
    deps.add(tree_dir / 222, entry.Notice(222))
    deps.add(tree_dir / 333, entry.Notice(333))
    deps.add(tree_dir / 333, entry.Version(333))
    assert not fill_with_rules.is_derived('111', deps, tree_dir)
    assert fill_with_rules.is_derived('222', deps, tree_dir)
    assert fill_with_rules.is_derived('333', deps, tree_dir)
    assert not fill_with_rules.is_derived('444', deps, tree_dir)


@pytest.mark.django_db
def test_process(monkeypatch):
    """Verify that the correct changes are found"""
    monkeypatch.setattr(fill_with_rules, 'compile_regulation',
                        Mock(return_value=Node()))
    monkeypatch.setattr(fill_with_rules, 'NoticeXML', Mock())
    fill_with_rules.NoticeXML.from_db.return_value.amendments = [
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

    tree_dir = entry.Tree('12', '1000')
    (tree_dir / 'old').write(Node())
    entry.Entry('notice_xml', 'new').write(b'')
    fill_with_rules.process(tree_dir, 'old', 'new')
    changes = dict(fill_with_rules.compile_regulation.call_args[0][1])
    assert changes == {"1000-2-b": ["2b changes"],
                       "1000-2-c": ["2c changes"],
                       "1000-4-a": ["4a changes"]}


def test_drop_initial_orphan_versions():
    version_list = [CFRVersion(identifier=letter) for letter in 'abcdef']
    version_pairs = list(zip(version_list, [None] + version_list[1:]))
    existing = {'c', 'e'}

    result = fill_with_rules.drop_initial_orphans(version_pairs, existing)
    result = [pair[0].identifier for pair in result]

    assert result == ['c', 'd', 'e', 'f']
