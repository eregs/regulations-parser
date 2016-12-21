import string

from pyparsing import FollowedBy, LineEnd, LineStart, Literal, SkipTo, Word

from regparser.grammar import atomic, unified, utils


def parenthesize(characters, name):
    return Literal("(") + Word(characters).setResultsName(name) + Literal(")")


def decimalize(characters, name):
    return (Word(characters).setResultsName(name) +
            Literal(".").leaveWhitespace())


#   Only used as the top of the appendix hierarchy
a1 = Word(string.digits).setResultsName("a1")
aI = Word("IVXLCDM").setResultsName("aI")


#   Catches the A in 12A but not in 12Awesome
markerless_upper = Word(string.ascii_uppercase).setResultsName(
    'markerless_upper') + ~FollowedBy(Word(string.ascii_lowercase))


paren_upper = parenthesize(string.ascii_uppercase, "paren_upper")
paren_lower = parenthesize(string.ascii_lowercase, "paren_lower")
paren_digit = parenthesize(string.digits, "paren_digit")


period_upper = decimalize(string.ascii_uppercase, "period_upper")
period_lower = decimalize(string.ascii_lowercase, "period_lower")
period_digit = decimalize(string.digits, "period_digit")


section = (
    atomic.section_marker.copy().leaveWhitespace() +
    unified.part_section +
    SkipTo(LineEnd())
)


par = (
    atomic.section.copy().leaveWhitespace() +
    unified.depth1_p +
    SkipTo(LineEnd())
)


marker_par = (
    atomic.paragraph_marker.copy().leaveWhitespace() +
    atomic.section +
    unified.depth1_p
)


appendix = (
    atomic.appendix_marker.copy().leaveWhitespace() +
    atomic.appendix +
    SkipTo(LineEnd())
)


headers = utils.QuickSearchable(
    LineStart() + (section | marker_par | par | appendix))
