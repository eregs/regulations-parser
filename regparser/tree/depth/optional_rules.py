"""Depth derivation has a mechanism for _optional_ rules. This module contains
a collection of such rules. All functions should accept two parameters; the
latter is a list of all variables in the system; the former is a function
which can be used to constrain the variables. This allows us to define rules
over subsets of the variables rather than all of them, should that make our
constraints more useful"""
from constraint import InSetConstraint

from regparser.tree.depth import markers
from regparser.tree.depth.rules import ancestors


def depth_type_inverses(constrain, all_variables):
    """If paragraphs are at the same depth, they must share the same type. If
    paragraphs are the same type, they must share the same depth"""
    def inner(typ, idx, depth, *all_prev):
        if typ == markers.stars or typ == markers.markerless:
            return True
        for i in range(0, len(all_prev), 3):
            prev_typ, prev_idx, prev_depth = all_prev[i:i+3]
            if prev_depth == depth and prev_typ not in (markers.stars, typ,
                                                        markers.markerless):
                return False
            if prev_typ == typ and prev_depth != depth:
                return False
        return True

    for i in range(0, len(all_variables), 3):
        constrain(inner, all_variables[i:i+3] + all_variables[:i])


def star_new_level(constrain, all_variables):
    """STARS should never have subparagraphs as it'd be impossible to
    determine where in the hierarchy these subparagraphs belong.
    @todo: This _probably_ should be a general rule, but there's a test that
    this breaks in the interpretations. Revisit with CFPB regs"""
    def inner(prev_typ, prev_depth, typ, depth):
        return not (prev_typ == markers.stars and depth == prev_depth + 1)

    for i in range(3, len(all_variables), 3):
        prev_typ, prev_depth = all_variables[i - 3], all_variables[i - 1]
        typ, depth = all_variables[i], all_variables[i + 2]
        constrain(inner, [prev_typ, prev_depth, typ, depth])


def limit_paragraph_types(*p_types):
    """Constraint paragraphs to a limited set of paragraph types. This can
    reduce the search space if we know (for example) that the text comes from
    regulations and hence does not have capitalized roman numerals"""
    def constrainer(constrain, all_variables):
        types = [all_variables[i] for i in range(0, len(all_variables), 3)]
        constrain(InSetConstraint(p_types), types)
    return constrainer


def gapless_sequence(constrain, all_variables):
    """We've loosened the rules around sequences of paragraphs so that
    paragraphs can be skipped. This rule tightens that again, requiring all
    normal paragraphs to progress in an unbroken sequence"""
    def inner(typ, idx, depth, *all_prev):
        ancestor_markers = ancestors(all_prev)
        # Continuing a sequence or becoming more shallow
        if depth < len(ancestor_markers):
            # Find the previous marker at this depth
            prev_typ, prev_idx, prev_depth = ancestor_markers[depth]
            types = set([prev_typ, typ])
            special_types = set([markers.stars, markers.markerless])
            if not special_types & types and prev_typ == typ:
                return idx == prev_idx + 1
        return True

    for i in range(0, len(all_variables), 3):
        constrain(inner, all_variables[i:i+3] + all_variables[:i])
