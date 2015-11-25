from datetime import date
from itertools import permutations
from unittest import TestCase

from regparser.history.versions import Version


class HistoryVersionsTest(TestCase):
    def test_order(self):
        v1 = Version('1111', date(2001, 1, 1), date(2001, 1, 1))
        v2 = Version('2222', date(2001, 1, 1), date(2002, 2, 2))
        v3 = Version('3333', date(2003, 3, 3), date(2002, 2, 2))
        v4 = Version('4444', date(2003, 3, 3), date(2002, 2, 2))

        for permutation in permutations([v1, v2, v3, v4]):
            self.assertEqual(sorted(permutation), [v1, v2, v3, v4])
