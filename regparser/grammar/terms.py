# -*- coding: utf-8 -*-
from pyparsing import (LineStart, Literal, OneOrMore, Optional, Regex, SkipTo,
                       Suppress, Word, ZeroOrMore, srange)

from regparser.grammar import atomic, unified
from regparser.grammar.utils import (DocLiteral, Marker, QuickSearchable,
                                     keep_pos)

smart_quotes = QuickSearchable(
    Suppress(DocLiteral(u'“', "left-smart-quote")) +
    keep_pos(SkipTo(DocLiteral(
        u'”', "right-smart-quote"))).setResultsName("term")
)

e_tag = (
    Suppress(Regex(r"<E[^>]*>")) +
    keep_pos(OneOrMore(Word(srange("[a-zA-Z-]")))).setResultsName("term") +
    Suppress(Literal("</E>"))
)

xml_term_parser = QuickSearchable(
    LineStart() +
    Optional(Suppress(unified.any_depth_p)) +
    e_tag.setResultsName("head") +
    ZeroOrMore(
        (atomic.conj_phrases + e_tag).setResultsName(
            "tail", listAllMatches=True)) +
    Suppress(ZeroOrMore(Regex(r",[a-zA-Z ]+,"))) +
    Suppress(ZeroOrMore(
        (Marker("this") | Marker("the")) + Marker("term"))) +
    ((Marker("mean") | Marker("means")) |
     (Marker("refers") + ZeroOrMore(Marker("only")) + Marker("to")) |
     ((Marker("has") | Marker("have")) + Marker("the") + Marker("same") +
      Marker("meaning") + Marker("as")))
)

key_term_parser = QuickSearchable(
    LineStart() +
    Optional(Suppress(unified.any_depth_p)) +
    Suppress(Regex(r"<E[^>]*>")) +
    keep_pos(OneOrMore(Word(srange("[a-zA-Z-,]")))).setResultsName("term") +
    Optional(Suppress(".")) +
    Suppress(Literal("</E>"))
)

scope_term_type_parser = QuickSearchable(
    Marker("purposes") + Marker("of") + Optional(Marker("this")) +
    SkipTo(",").setResultsName("scope") + Literal(",") +
    Optional(Marker("the") + Marker("term")) +
    keep_pos(
        SkipTo(Marker("means") | (Marker("refers") + Marker("to")))
    ).setResultsName("term"))
