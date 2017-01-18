from unittest import TestCase

from regparser.tree.depth import heuristics, markers
from regparser.tree.depth.derive import Solution


class HeuristicsTests(TestCase):
    def setUp(self):
        self.idx_counter = 0
        self.solution = {}

    def add_assignment(self, typ, char, depth):
        self.solution['type{0}'.format(self.idx_counter)] = typ
        self.solution['idx{0}'.format(self.idx_counter)] = typ.index(char)
        self.solution['depth{0}'.format(self.idx_counter)] = depth
        self.idx_counter += 1

    def test_prefer_multiple_children(self):
        """Should a trailing i be a roman numeral or a lower case?"""
        self.add_assignment(markers.lower, 'a', 0)
        self.add_assignment(markers.lower, 'b', 0)
        self.add_assignment(markers.lower, 'c', 0)
        self.add_assignment(markers.lower, 'd', 0)
        self.add_assignment(markers.lower, 'e', 0)
        self.add_assignment(markers.lower, 'f', 0)
        self.add_assignment(markers.lower, 'g', 0)
        self.add_assignment(markers.lower, 'h', 0)
        self.add_assignment(markers.lower, 'i', 0)

        solution1 = self.solution
        solution2 = solution1.copy()
        solution2['type8'] = markers.roman
        solution2['idx8'] = 0
        solution2['depth8'] = 1

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_multiple_children(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

    def test_prefer_diff_types_diff_levels(self):
        """Generally assume that the same depth only contains one type of
        marker"""
        self.add_assignment(markers.lower, 'h', 0)
        self.add_assignment(markers.ints, '1', 1)
        self.add_assignment(markers.roman, 'i', 2)
        self.add_assignment(markers.upper, 'A', 3)
        solution1 = self.solution

        self.setUp()

        self.add_assignment(markers.lower, 'h', 0)
        self.add_assignment(markers.ints, '1', 1)
        self.add_assignment(markers.roman, 'i', 0)
        self.add_assignment(markers.upper, 'A', 1)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_diff_types_diff_levels(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

    def test_prefer_shallow_depths(self):
        """Generate two solutions which vary only in depth. Verify that we
        prefer the more shallow"""
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.ints, '1', 1)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        solution1 = self.solution

        self.setUp()
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.ints, '1', 1)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 2)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_shallow_depths(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

    def test_prefer_no_markerless_sandwich(self):
        """Generate two solutions, one in which a markerless sandwich
        is used to skip depth, and another where it is not used to
        skip depth."""

        self.add_assignment(markers.ints, '1', 0)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 1)
        self.add_assignment(markers.roman, 'i', 1)
        solution1 = self.solution

        self.setUp()
        self.add_assignment(markers.ints, '1', 0)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 1)
        self.add_assignment(markers.roman, 'i', 2)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_no_markerless_sandwich(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

        self.setUp()
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.lower, 'a', 1)
        self.add_assignment(markers.lower, 'b', 1)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.lower, 'a', 1)
        self.add_assignment(markers.lower, 'b', 1)
        solution1 = self.solution

        self.setUp()
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 0)
        self.add_assignment(markers.lower, 'a', 1)
        self.add_assignment(markers.lower, 'b', 1)
        self.add_assignment(markers.markerless, markers.MARKERLESS, 2)
        self.add_assignment(markers.lower, 'a', 3)
        self.add_assignment(markers.lower, 'b', 3)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_no_markerless_sandwich(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)
