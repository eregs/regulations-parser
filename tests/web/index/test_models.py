from datetime import date
from itertools import permutations

from regparser.web.index.models import CFRVersion


def test_version_order1():
    """Versions should be correctly linearized"""
    versions = [
        CFRVersion(identifier='1111', effective=date(2004, 4, 4),
                   fr_volume=4, fr_page=4, cfr_title=12, cfr_part=1000),
        CFRVersion(identifier='2222', effective=date(2002, 2, 2),
                   fr_volume=4, fr_page=4, cfr_title=12, cfr_part=1000),
        CFRVersion(identifier='3333', effective=date(2004, 4, 4),
                   fr_volume=3, fr_page=3, cfr_title=12, cfr_part=1000)
    ]

    assert ['2222', '3333', '1111'] == [v.identifier for v in sorted(versions)]


def test_version_order2():
    """Versions should be correctly linearized"""
    versions = [
        CFRVersion(identifier='first', effective=date(2001, 1, 1),
                   fr_volume=1, fr_page=1),
        CFRVersion(identifier='eff', effective=date(2002, 2, 2),
                   fr_volume=1, fr_page=1),
        CFRVersion(identifier='cit', effective=date(2002, 2, 2),
                   fr_volume=3, fr_page=3),
        CFRVersion(identifier='cit >id', effective=date(2002, 2, 2),
                   fr_volume=3, fr_page=3),
    ]

    for permutation in permutations(versions):
        assert list(sorted(permutation)) == versions


def test_parents_of():
    final1 = CFRVersion(effective=date(2002, 2, 2), fr_volume=1, fr_page=1)
    prop1 = CFRVersion(fr_volume=2, fr_page=2)
    final2 = CFRVersion(effective=date(2004, 4, 4), fr_volume=3, fr_page=3)
    prop2 = CFRVersion(identifier='222', fr_volume=4, fr_page=4)
    prop3 = CFRVersion(identifier='333', fr_volume=6, fr_page=6)
    prop4 = CFRVersion(identifier='444', fr_volume=6, fr_page=6)

    correct_order = [final1, prop1, final2, prop2, prop3, prop4]
    for permutation in permutations(correct_order):
        assert list(sorted(permutation)) == correct_order
    paired = list(zip(correct_order, CFRVersion.parents_of(correct_order)))
    assert paired == [(final1, None), (prop1, final1), (final2, final1),
                      (prop2, final2), (prop3, final2), (prop4, final2)]
