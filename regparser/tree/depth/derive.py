from collections import namedtuple

from constraint import Problem

from regparser.tree.depth import markers, rules
from regparser.tree.depth.pair_rules import pair_rules
from regparser.tree.struct import Node

# A paragraph's type, index, depth assignment
ParAssignment = namedtuple('ParAssignment', ('typ', 'idx', 'depth'))


class Solution(object):
    """A collection of assignments + a weight for how likely this solution is
    (after applying heuristics)"""
    def __init__(self, assignment, weight=1.0):
        self.weight = weight
        self.assignment = []
        if isinstance(assignment, list):
            self.assignment = assignment
        else:   # assignment is a dict (as returned by constraint solver)
            for i in range(len(assignment) // 3):    # for (type, idx, depth)
                self.assignment.append(
                    ParAssignment(assignment['type' + str(i)],
                                  assignment['idx' + str(i)],
                                  assignment['depth' + str(i)]))

    def copy_with_penalty(self, penalty):
        """Immutable copy while modifying weight"""
        sol = Solution([], self.weight * (1 - penalty))
        sol.assignment = self.assignment
        return sol

    def __iter__(self):
        return iter(self.assignment)

    def pretty_str(self):
        return "\n".join(" " * 4 * par.depth + par.typ[par.idx]
                         for par in self.assignment)


def _compress_markerless(marker_list):
    """Remove repeated MARKERLESS markers. This will speed up depth
    computations as these paragraphs are redundant for its purposes"""
    result = []
    saw_markerless = False
    for marker in marker_list:
        if not Node.is_markerless_label([marker]):
            saw_markerless = False
            result.append(marker)
        elif not saw_markerless:
            saw_markerless = True
            result.append(marker)
    return result


def _decompress_markerless(assignment, marker_list):
    """Now that we have a specific solution, add back in the compressed
    MARKERLESS markers."""
    result = {}
    saw_markerless = False
    a_idx = -1      # idx in the assignment dict
    for m_idx, marker in enumerate(marker_list):
        if not Node.is_markerless_label([marker]):
            saw_markerless = False
            a_idx += 1
        elif not saw_markerless:
            saw_markerless = True
            a_idx += 1
        result['type{0}'.format(m_idx)] = assignment['type{0}'.format(a_idx)]
        result['idx{0}'.format(m_idx)] = assignment['idx{0}'.format(a_idx)]
        result['depth{0}'.format(m_idx)] = assignment['depth{0}'.format(a_idx)]
    return result


def derive_depths(original_markers, additional_constraints=None):
    """Use constraint programming to derive the paragraph depths associated
    with a list of paragraph markers. Additional constraints (e.g. expected
    marker types, etc.) can also be added. Such constraints are functions of
    two parameters, the constraint function (problem.addConstraint) and a
    list of all variables"""
    if additional_constraints is None:
        additional_constraints = []
    if not original_markers:
        return []
    problem = Problem()
    marker_list = _compress_markerless(original_markers)

    # Depth in the tree, with an arbitrary limit of 10
    problem.addVariables(["depth" + str(i) for i in range(len(marker_list))],
                         range(10))

    # Always start at depth 0
    problem.addConstraint(rules.must_be(0), ("depth0",))

    all_vars = []
    for idx, marker in enumerate(marker_list):
        type_var = "type{0}".format(idx)
        depth_var = "depth{0}".format(idx)
        # Index within the marker list. Though this variable is redundant, it
        # makes the code easier to understand and doesn't have a significant
        # performance penalty
        idx_var = "idx{0}".format(idx)

        typ_opts = [t for t in markers.types if marker in t]
        idx_opts = [i for t in typ_opts for i in range(len(t))
                    if t[i] == marker]
        problem.addVariable(type_var, typ_opts)
        problem.addVariable(idx_var, idx_opts)

        problem.addConstraint(rules.type_match(marker), [type_var, idx_var])
        all_vars.extend([type_var, idx_var, depth_var])

        if idx > 0:
            pairs = all_vars[3 * (idx - 1):]
            problem.addConstraint(pair_rules, pairs)

        if idx > 1:
            pairs = all_vars[3 * (idx - 2):]
            problem.addConstraint(rules.triplet_tests, pairs)

    # separate loop so that the simpler checks run first
    for idx in range(1, len(marker_list)):
        # start with the current idx
        params = all_vars[3 * idx:3 * (idx + 1)]
        # then add on all previous
        params += all_vars[:3 * idx]
        problem.addConstraint(rules.continue_previous_seq, params)

    # @todo: There's probably efficiency gains to making these rules over
    # prefixes (see above) rather than over the whole collection at once
    problem.addConstraint(rules.same_parent_same_type, all_vars)

    for constraint in additional_constraints:
        constraint(problem.addConstraint, all_vars)

    solutions = []
    for assignment in problem.getSolutionIter():
        assignment = _decompress_markerless(assignment, original_markers)
        solutions.append(Solution(assignment))
    return solutions


def debug_idx(marker_list, constraints=None):
    """Binary search through the markers to find the point at which
    derive_depths no longer works"""
    if constraints is None:
        constraints = []
    working, not_working = -1, len(marker_list)

    while working != not_working - 1:
        midpoint = (working + not_working) // 2
        solutions = derive_depths(marker_list[:midpoint + 1], constraints)
        if solutions:
            working = midpoint
        else:
            not_working = midpoint

    return not_working
