from constraint import Problem

from regparser.tree.depth import markers, rules


class ParAssignment(object):
    """A paragraph's type, index, depth assignment"""
    def __init__(self, typ, idx, depth):
        self.typ = typ
        self.idx = idx
        self.depth = depth


class Solution(object):
    """A collection of assignments + a weight for how likely this solution is
    (after applying heuristics)"""
    def __init__(self, assignment, weight=1.0):
        self.weight = weight
        self.assignment = []
        if isinstance(assignment, list):
            self.assignment = assignment
        else:   # assignment is a dict (as returned by constraint solver)
            for i in range(len(assignment) / 3):    # for (type, idx, depth)
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

    def pretty_print(self):
        for par in self.assignment:
            print " "*4*par.depth + par.typ[par.idx]


def derive_depths(marker_list, additional_constraints=[]):
    """Use constraint programming to derive the paragraph depths associated
    with a list of paragraph markers. Additional constraints (e.g. expected
    marker types, etc.) can also be added. Such constraints are functions of
    two parameters, the constraint function (problem.addConstraint) and a
    list of all variables"""
    if not marker_list:
        return []
    problem = Problem()

    # Depth in the tree, with an arbitrary limit of 10
    problem.addVariables(["depth" + str(i) for i in range(len(marker_list))],
                         range(10))

    # Always start at depth 0
    problem.addConstraint(rules.must_be(0), ("depth0",))

    all_vars = []
    for idx, marker in enumerate(marker_list):
        type_var = "type{}".format(idx)
        depth_var = "depth{}".format(idx)
        # Index within the marker list. Though this variable is redundant, it
        # makes the code easier to understand and doesn't have a significant
        # performance penalty
        idx_var = "idx{}".format(idx)

        typ_opts = [t for t in markers.types if marker in t]
        idx_opts = [i for t in typ_opts for i in range(len(t))
                    if t[i] == marker]
        problem.addVariable(type_var, typ_opts)
        problem.addVariable(idx_var, idx_opts)

        problem.addConstraint(rules.type_match(marker), [type_var, idx_var])
        all_vars.extend([type_var, idx_var, depth_var])

        if idx > 0:
            pairs = all_vars[3*(idx-1):]
            problem.addConstraint(rules.depth_check, pairs)
            problem.addConstraint(rules.stars_check, pairs)

        if idx > 1:
            pairs = all_vars[3*(idx-2):]
            problem.addConstraint(rules.markerless_sandwich, pairs)

    # separate loop so that the simpler checks run first
    for idx in range(1, len(marker_list)):
        # start with the current idx
        params = all_vars[3*idx:3*(idx+1)]
        # then add on all previous
        params += all_vars[:3*idx]
        problem.addConstraint(rules.sequence, params)

    # @todo: There's probably efficiency gains to making these rules over
    # prefixes (see above) rather than over the whole collection at once
    problem.addConstraint(rules.same_depth_same_type, all_vars)
    problem.addConstraint(rules.stars_occupy_space, all_vars)

    for constraint in additional_constraints:
        constraint(problem.addConstraint, all_vars)

    return [Solution(solution) for solution in problem.getSolutions()]
