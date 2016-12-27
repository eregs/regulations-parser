from unittest import TestCase

import six

from regparser.tree.depth import markers, optional_rules, rules
from regparser.tree.depth.derive import debug_idx, derive_depths
from regparser.tree.depth.markers import INLINE_STARS, MARKERLESS, STARS_TAG


class DeriveTests(TestCase):
    def assert_depth_match(self, markers, *depths_set):
        self.assert_depth_match_extra(markers, [], *depths_set)

    def assert_depth_match_extra(self, markers, extra, *depths_set):
        """Verify that the set of markers resolves to the provided set of
        depths (in any order). Allows extra constraints."""
        solutions = derive_depths(markers, extra)
        results = {tuple(a.depth for a in s) for s in solutions}
        six.assertCountEqual(self, results, {tuple(s) for s in depths_set})

    def test_ints(self):
        self.assert_depth_match(['1', '2', '3', '4'],
                                [0, 0, 0, 0])

    def test_alpha_ints(self):
        self.assert_depth_match(['A', '1', '2', '3'],
                                [0, 1, 1, 1])

    def test_alpha_ints_jump_back(self):
        self.assert_depth_match(['A', '1', '2', '3', 'B', '1', '2', '3', 'C'],
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
        self.assert_depth_match(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'],
                                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                [0, 0, 0, 0, 0, 0, 0, 0, 1])

        self.assert_depth_match(
            ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 0])

        self.assert_depth_match(
            ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'ii'],
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 1])

    def test_repeat_alpha(self):
        self.assert_depth_match(
            ['A', '1', 'a', 'i', 'ii', 'a', 'b', 'c', 'b'],
            [0, 1, 2, 3, 3, 4, 4, 4, 2])

    def test_simple_stars(self):
        self.assert_depth_match(['A', '1', STARS_TAG, 'd'],
                                [0, 1, 2, 2])

        self.assert_depth_match_extra(['A', '1', 'a', STARS_TAG, 'd'],
                                      [optional_rules.limit_sequence_gap()],
                                      [0, 1, 2, 2, 2])

    def test_ambiguous_stars(self):
        self.assert_depth_match(['A', '1', 'a', STARS_TAG, 'B'],
                                [0, 1, 2, 0, 0],
                                [0, 1, 2, 2, 0],
                                [0, 1, 2, 3, 3])
        self.assert_depth_match_extra(['A', '1', 'a', STARS_TAG, 'B'],
                                      [optional_rules.stars_occupy_space],
                                      [0, 1, 2, 2, 0],
                                      [0, 1, 2, 3, 3])

    def test_double_stars(self):
        self.assert_depth_match(['A', '1', 'a', STARS_TAG, STARS_TAG, 'B'],
                                [0, 1, 2, 1, 0, 0],
                                [0, 1, 2, 2, 0, 0],
                                [0, 1, 2, 2, 1, 0],
                                [0, 1, 2, 3, 0, 0],
                                [0, 1, 2, 3, 2, 0],
                                [0, 1, 2, 3, 1, 0])
        self.assert_depth_match_extra(
            ['A', '1', 'a', STARS_TAG, STARS_TAG, 'B'],
            [optional_rules.stars_occupy_space],
            [0, 1, 2, 2, 1, 0],
            [0, 1, 2, 3, 2, 0],
            [0, 1, 2, 3, 1, 0])

    def test_alpha_roman_ambiguous(self):
        self.assert_depth_match_extra(
            ['i', 'ii', STARS_TAG, 'v', STARS_TAG, 'vii'],
            [optional_rules.limit_sequence_gap()],
            [0, 0, 1, 1, 2, 2],
            [0, 0, 1, 1, 0, 0],
            [0, 0, 0, 0, 0, 0])

    def test_start_star(self):
        self.assert_depth_match_extra(
            [STARS_TAG, 'c', '1', STARS_TAG, 'ii', 'iii', '2', 'i', 'ii',
             STARS_TAG, 'v', STARS_TAG, 'vii', 'A'],
            [optional_rules.limit_sequence_gap()],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 3],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 3, 3, 2, 2, 3],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 3, 3, 4, 4, 5],
            [0, 0, 1, 2, 2, 2, 1, 2, 2, 0, 0, 1, 1, 2])

    def test_inline_star(self):
        self.assert_depth_match(['1', STARS_TAG, '2'],
                                [0, 0, 0],
                                [0, 1, 0])
        self.assert_depth_match_extra(['1', STARS_TAG, '2'],
                                      [optional_rules.stars_occupy_space],
                                      [0, 1, 0])

        self.assert_depth_match(['1', INLINE_STARS, '2'],
                                [0, 1, 0])

        self.assert_depth_match(['1', INLINE_STARS, 'a'],
                                [0, 1, 1])

    def test_star_star(self):
        self.assert_depth_match(['A', STARS_TAG, STARS_TAG, 'D'],
                                [0, 1, 0, 0])

        self.assert_depth_match(['A', INLINE_STARS, STARS_TAG, '3'],
                                [0, 1, 1, 1])

    def test_markerless_repeated(self):
        """Repeated markerless paragraphs must be on the same level"""
        self.assert_depth_match(
            [MARKERLESS, 'a', MARKERLESS, MARKERLESS],
            [0, 1, 0, 0],
            [0, 1, 2, 2])

    def test_ii_is_not_ambiguous(self):
        """We've fixed ii to be a roman numeral"""
        self.assert_depth_match(
            ['a', STARS_TAG, 'ii'],
            [0, 1, 1])

    def test_depth_type_order_single(self):
        """Constrain depths to have certain types."""
        extra = rules.depth_type_order([markers.ints, markers.lower])
        self.assert_depth_match_extra(['1', 'a'], [extra], [0, 1])
        self.assert_depth_match_extra(['i', 'a'], [extra])

    def test_depth_type_order_multiple(self):
        """Constrain depths to be in a list of types."""
        extra = rules.depth_type_order([(markers.ints, markers.roman),
                                        markers.lower])
        self.assert_depth_match_extra(['1', 'a'], [extra], [0, 1])
        self.assert_depth_match_extra(['i', 'a'], [extra], [0, 1])

    def test_depth_type_inverses_t2d(self):
        """Two markers of the same type should have the same depth"""
        self.assert_depth_match_extra(
            ['1', STARS_TAG, 'b', STARS_TAG, 'C', STARS_TAG, 'd'],
            [optional_rules.limit_sequence_gap()],
            [0, 1, 1, 2, 2, 3, 3],
            [0, 1, 1, 2, 2, 1, 1])

        self.assert_depth_match_extra(
            ['1', STARS_TAG, 'b', STARS_TAG, 'C', STARS_TAG, 'd'],
            [optional_rules.limit_sequence_gap(),
             optional_rules.depth_type_inverses],
            [0, 1, 1, 2, 2, 1, 1])

    def test_depth_type_inverses_d2t(self):
        """Two markers of the same depth should have the same type"""
        self.assert_depth_match_extra(
            ['1', STARS_TAG, 'c', '2', INLINE_STARS, 'i', STARS_TAG, 'iii'],
            [optional_rules.limit_sequence_gap()],
            [0, 1, 1, 0, 1, 1, 1, 1],
            [0, 1, 1, 0, 1, 1, 2, 2])

        self.assert_depth_match_extra(
            ['1', STARS_TAG, 'c', '2', INLINE_STARS, 'i', STARS_TAG, 'iii'],
            [optional_rules.limit_sequence_gap(),
             optional_rules.depth_type_inverses],
            [0, 1, 1, 0, 1, 1, 2, 2])

    def test_depth_type_inverses_markerless(self):
        """Markerless paragraphs should not trigger an incompatibility"""
        self.assert_depth_match_extra(
            ['1', MARKERLESS, '2', 'a'],
            [optional_rules.depth_type_inverses],
            [0, 1, 0, 1])

    def test_star_new_level(self):
        """STARS shouldn't have subparagraphs"""
        self.assert_depth_match(
            ['a', STARS_TAG, 'i'],
            [0, 0, 0],
            [0, 0, 1],
            [0, 1, 0],
            [0, 1, 1]
        )

        self.assert_depth_match_extra(
            ['a', STARS_TAG, 'i'],
            [optional_rules.star_new_level],
            [0, 0, 0],
            [0, 1, 0],
            [0, 1, 1]
        )

        self.assert_depth_match_extra(
            ['a', STARS_TAG, 'i'],
            [optional_rules.star_new_level, optional_rules.stars_occupy_space],
            [0, 0, 0],
            [0, 1, 0],
        )

    def test_marker_stars_markerless_symmetry(self):
        self.assert_depth_match(
            [MARKERLESS, 'a', STARS_TAG, MARKERLESS],
            [0, 1, 1, 0],
            [0, 1, 2, 2],
            [0, 1, 1, 2]
        )

    def test_markerless_stars_symmetry(self):
        self.assert_depth_match(
            [MARKERLESS, STARS_TAG, MARKERLESS],
            [0, 0, 0])

    def test_cap_roman(self):
        """Capitalized roman numerals can be paragraphs"""
        self.assert_depth_match(
            ['x', '1', 'A', 'i', 'I'],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 2])

    def test_limit_paragraph_types(self):
        """Limiting paragraph types limits how the markers are interpreted"""
        self.assert_depth_match(
            ['G', 'H', 'I'],
            [0, 0, 0],
            [0, 0, 1]
        )
        self.assert_depth_match_extra(
            ['G', 'H', 'I'],
            [optional_rules.limit_paragraph_types(markers.upper)],
            [0, 0, 0]
        )

    def test_markerless_at_beginning(self):
        """Allow markerless paragraphs to be on the same level as a paragraph
        marker"""
        self.assert_depth_match(
            [MARKERLESS, MARKERLESS, 'a'],
            [0, 0, 1],
            [0, 0, 0])
        self.assert_depth_match(
            [MARKERLESS, MARKERLESS, 'a', 'b', 'c', 'd'],
            [0, 0, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0])

    def test_limit_sequence_gap(self):
        """The limit_sequence_gap rule should limit our ability to derive
        depths with gaps between adjacent paragraphs. It should be
        configurable to allow any value"""
        self.assert_depth_match(['a', '1', 'i'],
                                [0, 1, 2],
                                [0, 1, 0])

        self.assert_depth_match_extra(['a', '1', 'i'],
                                      [optional_rules.limit_sequence_gap()],
                                      [0, 1, 2])

        self.assert_depth_match_extra(['a', '1', 'i'],
                                      [optional_rules.limit_sequence_gap(10)],
                                      [0, 1, 2],
                                      [0, 1, 0])

    def test_debug_idx(self):
        """Find the index of the first error when attempting to derive
        depths"""
        self.assertEqual(debug_idx(['1', '2', '3']), 3)
        self.assertEqual(debug_idx(['1', 'c']), 1)
        self.assertEqual(debug_idx(['1', '2', 'c']), 2)
        self.assertEqual(
            debug_idx(['1', 'a', '2', 'A'],
                      [optional_rules.depth_type_inverses]),
            3)
