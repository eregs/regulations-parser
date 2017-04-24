from datetime import date

import pytest
from mock import Mock
from model_mommy import mommy

from regparser.commands import fill_with_rules
from regparser.tree.struct import Node
from regparser.web.index.models import CFRVersion, Document, SourceFile


@pytest.mark.django_db
def test_save_tree(monkeypatch):
    """Expect constructed trees to depend on their predecessor, associated
    document and version files."""
    monkeypatch.setattr(fill_with_rules, 'NoticeXML', Mock())
    monkeypatch.setattr(fill_with_rules, 'doc_to_tree', Mock())
    fill_with_rules.NoticeXML.return_value.amendments = [
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
    monkeypatch.setattr(fill_with_rules, 'compile_regulation',
                        Mock(return_value=Node(label=['1000'])))
    version = mommy.make(CFRVersion,
                         source=mommy.make(SourceFile, contents=b'<ROOT/>'))
    parent = mommy.make(Document)

    fill_with_rules.save_tree(version, parent)
    changes = dict(fill_with_rules.compile_regulation.call_args[0][1])
    assert changes == {"1000-2-b": ["2b changes"],
                       "1000-2-c": ["2c changes"],
                       "1000-4-a": ["4a changes"]}

    assert version.doc is not None
    assert version.doc.collection == 'gpo_cfr'
    assert version.doc.label == '1000'
    assert version.doc.source == version.source
    assert version.doc.version == version
    assert version.doc.previous_document == parent
    assert len(version.doc.contents) > 0


class VersionFactory:
    def __init__(self):
        self.counter = 0

    def __call__(self, collection):
        self.counter += 1
        return mommy.make(
            CFRVersion, identifier=str(self.counter)*3, cfr_title=12,
            cfr_part=1000, effective=date(2010, 1, self.counter),
            source=mommy.make(SourceFile, collection=collection)
        )


@pytest.mark.django_db
def test_build_pairs_only_necessary():
    """Should filter versions to find only those that need a document"""
    factory = VersionFactory()
    v111 = factory('gpo_cfr')
    mommy.make(Document, version=v111)
    v222 = factory('notice')
    v333 = factory('notice')
    v444 = factory('notice')
    mommy.make(Document, version=v444)

    results = fill_with_rules.build_pairs(12, 1000)

    assert results == [(v222, v111), (v333, v222)]


@pytest.mark.django_db
def test_build_pairs_initial_orphan_versions():
    """We can't fill in data until we hit a version which *has* a document"""
    factory = VersionFactory()
    [v1, v2, v3, v4, v5, v6, v7] = [factory('notice') for _ in range(7)]
    mommy.make(Document, version=v3)
    mommy.make(Document, version=v5)

    results = fill_with_rules.build_pairs(12, 1000)

    assert results == [(v4, v3), (v6, v5), (v7, v6)]
