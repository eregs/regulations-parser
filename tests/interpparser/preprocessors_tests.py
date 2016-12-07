# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from interpparser import preprocessors
from regparser.test_utils.xml_builder import XMLBuilder


def test_supplement_amdpar_incorrect_ps():
    """Supplement I AMDPARs are not always labeled as should be"""
    with XMLBuilder("PART") as ctx:
        with ctx.REGTEXT():
            ctx.AMDPAR("1. In § 105.1, revise paragraph (b):")
            with ctx.SECTION():
                ctx.STARS()
                ctx.P("(b) Content")
            ctx.P("2. In Supplement I to Part 105,")
            ctx.P("A. Under Section 105.1, 1(b), paragraph 2 is revised")
            ctx.P("The revisions are as follows")
            ctx.HD("Supplement I to Part 105", SOURCE="HD1")
            ctx.STARS()
            with ctx.P():
                ctx.E("1(b) Heading", T="03")
            ctx.STARS()
            ctx.P("2. New Context")

    preprocessors.supplement_amdpar(ctx.xml)

    # Note that the SECTION paragraphs were not converted
    assert [amd.text for amd in ctx.xml.xpath("//AMDPAR")] == [
        "1. In § 105.1, revise paragraph (b):",
        "2. In Supplement I to Part 105,",
        "A. Under Section 105.1, 1(b), paragraph 2 is revised",
        "The revisions are as follows"
    ]
