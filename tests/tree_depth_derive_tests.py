from unittest import TestCase

from regparser.tree.depth import markers, rules
from regparser.tree.depth.derive import derive_depths
from regparser.tree.depth.markers import STARS_TAG, INLINE_STARS


class DeriveTests(TestCase):
    def assert_depth_match(self, markers, *depths_set):
        """Verify that the set of markers resolves to the provided set of
        depths (in any order)"""
        solutions = derive_depths(markers)
        results = [[a.depth for a in s] for s in solutions]
        self.assertEqual(len(depths_set), len(results))
        self.assertItemsEqual(results, depths_set)

    def test_ints(self):
        self.assert_depth_match(
            ['1', '2', '3', '4'],
            [0, 0, 0, 0])

    def test_alpha_ints(self):
        self.assert_depth_match(
            ['A', '1', '2', '3'],
            [0, 1, 1, 1])

    def test_alpha_ints_jump_back(self):
        self.assert_depth_match(
            ['A', '1', '2', '3', 'B', '1', '2', '3', 'C'],
            [0, 1, 1, 1, 0, 1, 1, 1, 0])

    def test_roman_alpha(self):
        self.assert_depth_match(
            ['a', '1', '2', 'b', '1', '2', '3', '4', 'i', 'ii', 'iii', '5',
             'c', 'd', '1', '2', 'e'],
            [0, 1, 1, 0, 1, 1, 1, 1, 2, 2, 2, 1, 0, 0, 1, 1, 0])

    def test_mix_levels_roman_alpha(self):
        self.assert_depth_match(
            ['A', '1', '2', 'i', 'ii', 'iii', 'iv', 'B', '1', 'a', 'b', '2',
             'a', 'b', 'i', 'ii', 'iii', 'c'],
            [0, 1, 1, 2, 2, 2, 2, 0, 1, 2, 2, 1, 2, 2, 3, 3, 3, 2])

    def test_i_ambiguity(self):
        self.assert_depth_match(
            ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 1])

        self.assert_depth_match(
            ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        self.assert_depth_match(
            ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'ii'],
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 1])

    def test_repeat_alpha(self):
        self.assert_depth_match(
            ['A', '1', 'a', 'i', 'ii', 'a', 'b', 'c', 'b'],
            [0, 1, 2, 3, 3, 4, 4, 4, 2])

    def test_simple_stars(self):
        self.assert_depth_match(
            ['A', '1', STARS_TAG, 'd'],
            [0, 1, 2, 2])

        self.assert_depth_match(
            ['A', '1', 'a', STARS_TAG, 'd'],
            [0, 1, 2, 2, 2])

    def test_ambiguous_stars(self):
        self.assert_depth_match(
            ['A', '1', 'a', STARS_TAG, 'B'],
            [0, 1, 2, 3, 3],
            [0, 1, 2, 3, 0],
            [0, 1, 2, 2, 0],
            [0, 1, 2, 1, 0])

    def test_double_stars(self):
        self.assert_depth_match(
            ['A', '1', 'a', STARS_TAG, STARS_TAG, 'B'],
            [0, 1, 2, 2, 1, 0],
            [0, 1, 2, 3, 2, 0],
            [0, 1, 2, 3, 1, 0])

    def test_alpha_roman_ambiguous(self):
        self.assert_depth_match(
            ['i', 'ii', STARS_TAG, 'v', STARS_TAG, 'vii'],
            [0, 0, 1, 1, 2, 2],
            [0, 0, 1, 1, 0, 0],
            [0, 0, 0, 0, 0, 0])

    def test_start_star(self):
        self.assert_depth_match(
            [STARS_TAG, 'c', '1', STARS_TAG, 'ii', 'iii', '2', 'i', 'ii',
             STARS_TAG, 'v', STARS_TAG, 'vii', 'A'],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 3],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 3, 3, 2, 2, 3],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 3, 3, 4, 4, 5],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 0, 0, 1, 1, 2])

    def test_inline_star(self):
        self.assert_depth_match(
            ['1', STARS_TAG, '2'],
            [0, 1, 0])

        self.assert_depth_match(
            ['1', INLINE_STARS, '2'],
            [0, 0, 0],
            [0, 1, 0])

    def test_star_star(self):
        self.assert_depth_match(
            ['A', STARS_TAG, STARS_TAG, 'D'],
            [0, 1, 0, 0])

        self.assert_depth_match(
            ['A', INLINE_STARS, STARS_TAG, 'D'],
            [0, 1, 2, 2],
            [0, 1, 0, 0])

    def test_depth_type_order(self):
        extra = rules.depth_type_order([markers.ints, markers.lower])
        results = derive_depths(['1', 'a'], [extra])
        self.assertEqual(1, len(results))
        results = derive_depths(['i', 'a'], [extra])
        self.assertEqual(0, len(results))

        extra = rules.depth_type_order([(markers.ints, markers.roman),
                                        markers.lower])
        results = derive_depths(['1', 'a'], [extra])
        self.assertEqual(1, len(results))
        results = derive_depths(['i', 'a'], [extra])
        self.assertEqual(1, len(results))
