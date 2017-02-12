from datetime import date

import pytest

from regparser.commands import layers
from regparser.history.versions import Version
from regparser.index import dependency, entry
from regparser.notice.citation import Citation
from regparser.tree.struct import Node


@pytest.mark.django_db
def test_stale_layers(monkeypatch):
    """We should have dependencies between all of the layers and their
    associated trees. We should also tie the meta layer to the version"""
    monkeypatch.setattr(layers, 'LAYER_CLASSES',
                        {'cfr': {'keyterms': None, 'other': None}})

    version_entry = entry.Version(111, 22, 'aaa')
    version_entry.write(Version('aaa', date.today(), Citation(1, 1)))
    tree_entry = entry.Tree(111, 22, 'aaa')
    with pytest.raises(dependency.Missing):
        layers.stale_layers(tree_entry, 'cfr')

    entry.Entry('tree', 111, 22, 'bbb').write(b'')    # wrong version
    with pytest.raises(dependency.Missing):
        layers.stale_layers(tree_entry, 'cfr')

    entry.Entry('tree', 111, 22, 'aaa').write(b'')
    assert set(layers.stale_layers(tree_entry, 'cfr')) == {'keyterms', 'other'}

    assert str(version_entry) in dependency.Graph().dependencies(
        str(entry.Layer.cfr(111, 22, 'aaa', 'meta')))


@pytest.mark.django_db
def test_process_cfr_layers():
    """All layers for a single version should get written."""
    version_entry = entry.Version(12, 1000, '1234')
    version_entry.write(Version('1234', date.today(), Citation(1, 1)))
    entry.Tree('12', '1000', '1234').write(Node())

    layers.process_cfr_layers(['keyterms', 'meta'], 12, version_entry)

    assert entry.Layer.cfr(12, 1000, '1234', 'keyterms').exists()
    assert entry.Layer.cfr(12, 1000, '1234', 'meta').exists()


@pytest.mark.django_db
def test_process_preamble_layers():
    """All layers for a single preamble should get written."""
    preamble_entry = entry.Preamble('111_222')
    preamble_entry.write(Node())

    layers.process_preamble_layers(['graphics'], preamble_entry)

    assert entry.Layer.preamble('111_222', 'graphics').exists()
