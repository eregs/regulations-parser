"""Rules relating to two paragraph markers in sequence. The rules are
"positive" in the sense that each allows for a particular scenario (rather
than denying all other scenarios). They combine in the eponymous function,
where, if any of the rules return True, we pass. Otherwise, we fail."""
from collections import namedtuple

from regparser.tree.depth import markers


# @todo - this might be helpful in other rules, too
class MarkerAssignment(namedtuple('MarkerAssignment',
                                  ('typ', 'idx', 'depth'))):
    def is_markerless(self):
        """We will often check whether an assignment is MARKERLESS. This
        function makes that clearer"""
        return self.typ == markers.markerless

    def is_stars(self):
        """We will often check whether an assignment is either STARS or inline
        stars (* * *). This function makes that clearer"""
        return self.typ == markers.stars

    def is_inline_stars(self):
        """Inline stars (* * *) often behave quite differently from both STARS
        and other markers."""
        return self.is_stars() and self.idx == 1


def decrement_depth(prev, curr):
    """Decrementing depth is okay unless we're using inline stars"""
    return curr.depth < prev.depth and not curr.is_inline_stars()


def continuing_seq(prev, curr):
    """E.g. "d, e" is good, but "e, d" is not. We also want to allow some
    paragraphs to be skipped, e.g. "d, g" """
    return (curr.depth == prev.depth and
            curr.typ == prev.typ and
            curr.idx >= prev.idx + 1)


def decreasing_stars(prev, curr):
    """Two stars in a row can exist if the second is shallower than the
    first"""
    return prev.is_stars() and curr.is_stars() and curr.depth < prev.depth


def same_level_stars(prev, curr):
    """Two stars in a row can exist on the same level if the previous is
    inline"""
    two_stars = prev.is_stars() and curr.is_stars()
    return two_stars and prev.depth == curr.depth and prev.is_inline_stars()


def star_marker_level(prev, curr):
    """Allow markers to be on the same level as a preceding star"""
    return (prev.is_stars() and not curr.is_stars() and
            prev.depth == curr.depth)


def marker_star_level(prev, curr):
    """Allow a marker to be followed by stars if those stars are deeper. If
    not inline, also allow the stars to be at the same depth"""
    possible_depths = {prev.depth + 1}
    if curr.is_stars() and not curr.is_inline_stars():
        possible_depths.add(prev.depth)

    return (not prev.is_stars() and curr.is_stars() and
            curr.depth in possible_depths)


def new_sequence(prev, curr):
    """Allow depth to be incremented if starting a new sequence"""
    return (curr.idx == 0 and
            curr.depth == prev.depth + 1 and
            curr.typ != prev.typ)


def markerless_same_level(prev, curr):
    """Markerless paragraphs can be followed by any type on the same level as
    long as that's beginning a new sequence"""
    return (prev.is_markerless() and prev.depth == curr.depth and
            curr.idx == 0)


def paragraph_markerless(prev, curr):
    """A non-markerless paragraph followed by a markerless paragraph can be
    one level deeper"""
    return (not prev.is_markerless() and curr.is_markerless() and
            curr.depth == prev.depth + 1)


def pair_rules(prev_typ, prev_idx, prev_depth, typ, idx, depth):
    """Combine all of the above rules"""
    prev = MarkerAssignment(prev_typ, prev_idx, prev_depth)
    curr = MarkerAssignment(typ, idx, depth)
    fns = (decrement_depth, continuing_seq, decreasing_stars,
           same_level_stars, star_marker_level, marker_star_level,
           new_sequence, markerless_same_level, paragraph_markerless)
    return any(fn(prev, curr) for fn in fns)
