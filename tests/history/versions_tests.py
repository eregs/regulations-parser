from datetime import date
from itertools import permutations
from random import randrange

from regparser.history.versions import Version
from regparser.notice.citation import Citation


def test_order():
    v1 = Version('first', date(2001, 1, 1), Citation(1, 1))
    v2 = Version('eff', date(2002, 2, 2), Citation(1, 1))
    v3 = Version('cit', date(2002, 2, 2), Citation(3, 3))
    v4 = Version('cit >id', date(2002, 2, 2), Citation(3, 3))

    for permutation in permutations([v1, v2, v3, v4]):
        assert list(sorted(permutation)) == [v1, v2, v3, v4]


def test_parents_of():
    final1 = Version(str(randrange(1000)), date(2002, 2, 2), Citation(1, 1))
    prop1 = Version(str(randrange(1000)), None, Citation(2, 2))
    final2 = Version(str(randrange(1000)), date(2004, 4, 4), Citation(3, 3))
    prop2 = Version('222', None, Citation(4, 4))
    prop3 = Version('333', None, Citation(6, 6))
    prop4 = Version('444', None, Citation(6, 6))

    correct_order = [final1, prop1, final2, prop2, prop3, prop4]
    for permutation in permutations(correct_order):
        assert list(sorted(permutation)) == correct_order
    paired = list(zip(correct_order, Version.parents_of(correct_order)))
    assert paired == [(final1, None), (prop1, final1), (final2, final1),
                      (prop2, final2), (prop3, final2), (prop4, final2)]
