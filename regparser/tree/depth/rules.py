"""Namespace for constraints on paragraph depth discovery.

For the purposes of this module a "symmetry" refers to two perfectly valid
solutions to a problem whose differences are irrelevant. For example, if the
distinctions between
a           vs.     a
STARS                   STARS
may not matter if we're planning to ignore the final STARS anyway. To "break"
this symmetry, we explicitly reject one solution; this reduces the number of
permutations we care about dramatically.
"""
from regparser.tree.depth import markers
from regparser.tree.depth.pair_rules import pair_rules


def must_be(value):
    """A constraint that the given variable must matches the value."""
    def inner(var):
        return var == value
    return inner


def type_match(marker):
    """The type of the associated variable must match its marker. Lambda
    explanation as in the above rule."""
    return lambda typ, idx: idx < len(typ) and typ[idx] == marker


def marker_stars_markerless_symmetry(pprev_typ, pprev_idx, pprev_depth,
                                     prev_typ, prev_idx, prev_depth,
                                     typ, idx, depth):
    """
    When we have the following symmetry:
        a                       a                       a
    STARS           vs.         STARS       vs.             STARS
    MARKERLESS              MARKERLESS              MARKERLESS

    Prefer the middle
    """
    situation = (
        pprev_typ not in (markers.markerless, markers.stars) and
        prev_typ == markers.stars and typ == markers.markerless and
        pprev_depth > depth)
    preferred_solution = prev_depth == pprev_depth
    return not situation or preferred_solution


def markerless_stars_symmetry(pprev_typ, pprev_idx, pprev_depth,
                              prev_typ, prev_idx, prev_depth,
                              typ, idx, depth):
    """Given MARKERLESS, STARS, MARKERLESS want to break these symmetries:

        MARKERLESS                  MARKERLESS
        STARS               vs.         STARS
        MARKERLESS                  MARKERLESS

        Here, we don't really care about the distinction, so we'll opt for the
        former."""
    sandwich = (pprev_typ == typ == markers.markerless and
                prev_typ == markers.stars)
    preferred_solution = prev_depth <= depth
    return not sandwich or preferred_solution


def star_sandwich_symmetry(pprev_typ, pprev_idx, pprev_depth,
                           prev_typ, prev_idx, prev_depth,
                           typ, idx, depth):
    """Symmetry breaking constraint that places STARS tag at specific depth so
    that the resolution of

                    c
    ?   ?   ?   ?   ?   ?   <- Potential STARS depths
    5

    can only be one of
                                OR
                    c                               c
                    STARS           STARS
    5                               5
    Stars also cannot be used to skip a level (similar to markerless sandwich,
    above)"""
    sandwich = (pprev_typ != markers.stars and typ != markers.stars and
                prev_typ == markers.stars)
    unwinding = prev_idx == 0 and pprev_depth > depth
    bad_unwinding = unwinding and prev_depth not in (pprev_depth, depth)
    inc_depth = depth == prev_depth + 1 and prev_depth == pprev_depth + 1
    return not (sandwich and (bad_unwinding or inc_depth))


def triplet_tests(*triplet_seq):
    """Run propositions around a sequence of three markers. We combine them
    here so that they act as a single constraint"""
    return (
        star_sandwich_symmetry(*triplet_seq) and
        marker_stars_markerless_symmetry(*triplet_seq) and
        markerless_stars_symmetry(*triplet_seq)
    )


def continue_previous_seq(typ, idx, depth, *all_prev):
    """Constrain the current marker based on all markers leading up to it"""
    ancestor_markers = ancestors(all_prev)
    # Becoming more shallow
    if depth < len(ancestor_markers) - 1:
        # Find the previous marker at this depth
        prev_typ, prev_idx, prev_depth = ancestor_markers[depth]
        return pair_rules(prev_typ, prev_idx, prev_depth, typ, idx, depth)
    else:
        return True


def same_parent_same_type(*all_vars):
    """All markers in the same parent should have the same marker type.
    Exceptions for:
        STARS, which can appear at any level
        Sequences which _begin_ with markerless paragraphs"""
    elements = [tuple(all_vars[i:i + 3]) for i in range(0, len(all_vars), 3)]

    def per_level(elements, parent_type=None):
        level, grouped_children = _level_and_children(elements)

        if not level:
            return True     # Base Case

        types = [typ for typ, idx, depth in level if not typ == markers.stars]
        if parent_type in types:
            return False

        last_type = markers.markerless
        for typ in types:
            if last_type != typ and last_type != markers.markerless:
                return False
            last_type = typ

        for children in grouped_children:           # Recurse
            if not per_level(children, types[0] if types else None):
                return False
        return True

    return per_level(elements)


def depth_type_order(order):
    """Create a function which constrains paragraphs depths to a particular
    type sequence. For example, we know a priori what regtext and
    interpretation markers' order should be. Adding this constrain speeds up
    solution finding."""
    order = list(order)     # defensive copy

    def inner(constrain, all_variables):
        for i in range(0, len(all_variables) // 3):
            constrain(lambda t, d: (d < len(order) and
                                    (t in (markers.stars, order[d]) or
                                     t in order[d])),
                      ('type' + str(i), 'depth' + str(i)))

    return inner


def ancestors(all_prev):
    """Given an assignment of values, construct a list of the relevant
    parents, e.g. 1, i, a, ii, A gives us 1, ii, A"""
    # Group (type, idx, depth) per marker
    all_prev = [tuple(all_prev[i:i + 3]) for i in range(0, len(all_prev), 3)]

    result = [None] * 10
    for prev_type, prev_idx, prev_depth in all_prev:
        result[prev_depth] = (prev_type, prev_idx, prev_depth)
        result[prev_depth + 1:] = [None] * (10 - prev_depth)
    return [r for r in result if r]


def _level_and_children(elements):
    """Split a list of elements into elements on the current level (i.e.
    that share the same depth as the first element) and segmented children
    (children of each of those elements)"""
    if not elements:        # Base Case
        return [], []
    depth = elements[0][2]
    level = []
    grouped_children = []
    children = []

    for el in elements:
        if el[2] == depth:
            level.append(el)
            if children:
                grouped_children.append(children)
            children = []
        else:
            children.append(el)
    if children:
        grouped_children.append(children)

    return level, grouped_children
