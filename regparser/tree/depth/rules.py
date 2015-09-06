"""Namespace for constraints on paragraph depth discovery"""

from regparser.tree.depth import markers


def must_be(value):
    """A constraint that the given variable must matches the value."""
    def inner(var):
        return var == value
    return inner


def type_match(marker):
    """The type of the associated variable must match its marker. Lambda
    explanation as in the above rule."""
    return lambda typ, idx: idx < len(typ) and typ[idx] == marker


def depth_check(prev_typ, prev_idx, prev_depth, typ, idx, depth):
    """Constrain the depth of sequences of markers."""
    # decrementing depth is always okay
    dec = depth < prev_depth
    # continuing a sequence
    cont = depth == prev_depth and prev_typ == typ and idx == prev_idx + 1
    # stars are also allowed if at the same level
    stars = depth == prev_depth and markers.stars in (typ, prev_typ)
    # depth can be incremented if starting a new sequence
    inc = depth == prev_depth + 1 and idx == 0 and typ != prev_typ
    # stars can also increment the depth
    next_star = depth == prev_depth + 1 and typ == markers.stars
    # markerless in sequence must have the same level
    mless_seq = (prev_typ == typ and prev_depth == depth
                 and typ == markers.markerless)
    return dec or cont or stars or inc or next_star or mless_seq


def stars_check(prev_typ, prev_idx, prev_depth, typ, idx, depth):
    """Constrain pairs of markers where one is a star."""
    if prev_typ == typ and typ == markers.stars:
        # Stars can't be on the same level in sequence
        dec = depth < prev_depth
        # and can only increase the depth in the previous was INLINE
        inc = prev_idx == 1 and depth == prev_depth + 1
        return dec or inc
    return True


def markerless_sandwich(pprev_typ, pprev_idx, pprev_depth,
                        prev_typ, prev_idx, prev_depth,
                        typ, idx, depth):
    """MARKERLESS shouldn't be used to skip a depth, like:
        a
            MARKERLESS
                a
    """
    sandwich = prev_typ == markers.markerless
    inc_depth = depth == prev_depth + 1 and prev_depth == pprev_depth + 1
    return not (sandwich and inc_depth)


def sequence(typ, idx, depth, *all_prev):
    """Constrain the current marker based on all markers leading up to it"""
    # Group (type, idx, depth) per marker
    all_prev = [tuple(all_prev[i:i+3]) for i in range(0, len(all_prev), 3)]
    prev_typ, prev_idx, prev_depth = all_prev[-1]

    if typ == markers.stars:    # Accounted for elsewhere
        return True
    # If following stars and on the same level, we're good
    elif (typ != prev_typ and prev_typ == markers.stars and
            depth == prev_depth):
        return True     # Stars
    elif typ == markers.markerless:
        if typ == prev_typ:
            return depth == prev_depth
        else:
            return depth <= prev_depth + 1
    else:
        ancestors = _ancestors(all_prev)
        # Starting a new sequence
        if len(ancestors) == depth:
            return idx == 0 and typ != prev_typ
        elif len(ancestors) > depth:
            prev_typ, prev_idx, prev_depth = ancestors[depth]
            return idx == prev_idx + 1 and prev_typ == typ
    return False


def same_parent_same_type(*all_vars):
    """All markers in the same level (with the same parent) should have the
    same marker type"""
    elements = [tuple(all_vars[i:i+3]) for i in range(0, len(all_vars), 3)]

    def per_level(elements, last_type=None):
        level, grouped_children = _level_and_children(elements)

        if not level:
            return True     # Base Case

        types = set(el[0] for el in level)
        types = list(sorted(types, key=lambda t: t == markers.stars))
        if len(types) > 2:
            return False
        if len(types) == 2 and markers.stars not in types:
            return False
        if last_type in types and last_type != markers.stars:
            return False
        for children in grouped_children:           # Recurse
            if not per_level(children, types[0]):
                return False
        return True

    return per_level(elements)


def stars_occupy_space(*all_vars):
    """Star markers can't be ignored in sequence, so 1, *, 2 doesn't make
    sense for a single level, unless it's an inline star. In the inline
    case, we can think of it as 1, intro-text-to-1, 2"""
    elements = [tuple(all_vars[i:i+3]) for i in range(0, len(all_vars), 3)]

    def per_level(elements):
        level, grouped_children = _level_and_children(elements)

        if not level:
            return True     # Base Case

        last_idx = -1
        for typ, idx, _ in level:
            if typ == markers.stars:
                if idx == 0:    # STARS_TAG, not INLINE_STARS
                    last_idx += 1
            elif last_idx >= idx and typ != markers.markerless:
                return False
            else:
                last_idx = idx

        for children in grouped_children:           # Recurse
            if not per_level(children):
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
        for i in range(0, len(all_variables) / 3):
            constrain(lambda t, d: (d < len(order)
                                    and (t in (markers.stars, order[d])
                                         or t in order[d])),
                      ('type' + str(i), 'depth' + str(i)))

    return inner


def global_same_depth_same_type(constrain, all_variables):
    def inner(typ, idx, depth, *all_prev):
        if typ == markers.stars:
            return True
        for i in range(0, len(all_prev), 3):
            prev_typ, prev_idx, prev_depth = all_prev[i:i+3]
            if prev_depth == depth and prev_typ not in (markers.stars, typ):
                return False
        return True

    for i in range(0, len(all_variables), 3):
        constrain(inner, all_variables[i:i+3] + all_variables[:i])


def _ancestors(all_prev):
    """Given an assignment of values, construct a list of the relevant
    parents, e.g. 1, i, a, ii, A gives us 1, ii, A"""
    result = [None]*10
    for prev_type, prev_idx, prev_depth in all_prev:
        result[prev_depth] = (prev_type, prev_idx, prev_depth)
        result[prev_depth + 1:] = [None]*(10 - prev_depth)
    result = filter(bool, result)
    return result


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
