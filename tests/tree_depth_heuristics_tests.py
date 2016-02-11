from unittest import TestCase

from regparser.tree.depth import heuristics, markers
from regparser.tree.depth.derive import Solution


class HeuristicsTests(TestCase):
    def setUp(self):
        self.idx_counter = 0
        self.solution = {}

    def addAssignment(self, typ, char, depth):
        self.solution['type{}'.format(self.idx_counter)] = typ
        self.solution['idx{}'.format(self.idx_counter)] = typ.index(char)
        self.solution['depth{}'.format(self.idx_counter)] = depth
        self.idx_counter += 1

    def test_prefer_multiple_children(self):
        """Should a trailing i be a roman numeral or a lower case?"""
        self.addAssignment(markers.lower, 'a', 0)
        self.addAssignment(markers.lower, 'b', 0)
        self.addAssignment(markers.lower, 'c', 0)
        self.addAssignment(markers.lower, 'd', 0)
        self.addAssignment(markers.lower, 'e', 0)
        self.addAssignment(markers.lower, 'f', 0)
        self.addAssignment(markers.lower, 'g', 0)
        self.addAssignment(markers.lower, 'h', 0)
        self.addAssignment(markers.lower, 'i', 0)

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
        self.addAssignment(markers.lower, 'h', 0)
        self.addAssignment(markers.ints, '1', 1)
        self.addAssignment(markers.roman, 'i', 2)
        self.addAssignment(markers.upper, 'A', 3)
        solution1 = self.solution

        self.setUp()

        self.addAssignment(markers.lower, 'h', 0)
        self.addAssignment(markers.ints, '1', 1)
        self.addAssignment(markers.roman, 'i', 0)
        self.addAssignment(markers.upper, 'A', 1)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_diff_types_diff_levels(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

    def test_prefer_shallow_depths(self):
        """Generate two solutions which vary only in depth. Verify that we
        prefer the more shallow"""
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.ints, '1', 1)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        solution1 = self.solution

        self.setUp()
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.ints, '1', 1)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 2)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_shallow_depths(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

    def test_prefer_no_markerless_sandwich(self):
        """Generate two solutions, one in which a markerless sandwich
        is used to skip depth, and another where it is not used to
        skip depth."""

        self.addAssignment(markers.ints, '1', 0)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 1)
        self.addAssignment(markers.roman, 'i', 1)
        solution1 = self.solution

        self.setUp()
        self.addAssignment(markers.ints, '1', 0)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 1)
        self.addAssignment(markers.roman, 'i', 2)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_no_markerless_sandwich(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)

        self.setUp()
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.lower, 'a', 1)
        self.addAssignment(markers.lower, 'b', 1)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.lower, 'a', 1)
        self.addAssignment(markers.lower, 'b', 1)
        solution1 = self.solution

        self.setUp()
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 0)
        self.addAssignment(markers.lower, 'a', 1)
        self.addAssignment(markers.lower, 'b', 1)
        self.addAssignment(markers.markerless, markers.MARKERLESS, 2)
        self.addAssignment(markers.lower, 'a', 3)
        self.addAssignment(markers.lower, 'b', 3)
        solution2 = self.solution

        solutions = [Solution(solution1), Solution(solution2)]
        solutions = heuristics.prefer_no_markerless_sandwich(solutions, 0.5)
        self.assertEqual(solutions[0].weight, 1.0)
        self.assertTrue(solutions[1].weight < solutions[0].weight)
