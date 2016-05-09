from datetime import date
from itertools import permutations
from random import randrange
from unittest import TestCase

from regparser.history.versions import Version


class HistoryVersionsTest(TestCase):
    def test_order(self):
        v1 = Version('first', date(2001, 1, 1), date(2001, 1, 1))
        v2 = Version('eff', date(2001, 1, 1), date(2002, 2, 2))
        v3 = Version('pub', date(2003, 3, 3), date(2002, 2, 2))
        v4 = Version('pub >id', date(2003, 3, 3), date(2002, 2, 2))

        for permutation in permutations([v1, v2, v3, v4]):
            self.assertEqual(sorted(permutation), [v1, v2, v3, v4])

    def test_parents_of(self):
        final1 = Version(str(randrange(1000)),
                         date(2001, 1, 1), date(2002, 2, 2))
        prop1 = Version(str(randrange(1000)), date(2001, 6, 6), None)
        final2 = Version(str(randrange(1000)),
                         date(2003, 3, 3), date(2004, 4, 4))
        prop2 = Version('222', date(2003, 4, 4), None)
        prop3 = Version('333', date(2006, 6, 6), None)
        prop4 = Version('444', date(2006, 6, 6), None)

        correct_order = [final1, prop1, final2, prop2, prop3, prop4]
        for permutation in permutations(correct_order):
            self.assertEqual(sorted(permutation), correct_order)
        paired = list(zip(correct_order, Version.parents_of(correct_order)))
        self.assertEqual(
            paired,
            [(final1, None), (prop1, final1), (final2, final1),
             (prop2, final2), (prop3, final2), (prop4, final2)])
