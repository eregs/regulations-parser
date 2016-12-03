# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.gpo_cfr import subpart as builder


def test_build_subpart():
    with XMLBuilder("SUBPART") as ctx:
        ctx.HD("Subpart A—First subpart")
        with ctx.SECTION():
            ctx.SECTNO("§ 8675.309")
            ctx.SUBJECT("Definitions.")
            ctx.P("Some content about this section.")
            ctx.P("(a) something something")
        with ctx.SECTION():
            ctx.SECTNO("§ 8675.310")
            ctx.SUBJECT("Definitions.")
            ctx.P("Some content about this section.")
            ctx.P("(a) something something")
    subpart = builder.build_subpart('8675', ctx.xml)
    assert subpart.node_type == 'subpart'
    assert len(subpart.children) == 2
    assert subpart.label == ['8675', 'Subpart', 'A']
    child_labels = [c.label for c in subpart.children]
    assert child_labels == [['8675', '309'], ['8675', '310']]


def test_build_subjgrp():
    with XMLBuilder("SUBJGRP") as ctx:
        ctx.HD("Changes of Ownership")
        with ctx.SECTION():
            ctx.SECTNO("§ 479.42")
            ctx.SUBJECT("Changes through death of owner.")
            ctx.P("Whenever any person who has paid […] conditions.")
        with ctx.SECTION():
            ctx.SECTNO("§ 479.43")
            ctx.SUBJECT("Changes through bankruptcy of owner.")
            ctx.P("A receiver or referee in bankruptcy may […] paid.")
            ctx.P("(a) something something")
    subpart = builder.build_subjgrp('479', ctx.xml, [])
    assert subpart.node_type == 'subpart'
    assert len(subpart.children) == 2
    assert subpart.label == ['479', 'Subjgrp', 'CoO']
    child_labels = [c.label for c in subpart.children]
    assert child_labels == [['479', '42'], ['479', '43']]


def test_get_subpart_group_title():
    with XMLBuilder("SUBPART") as ctx:
        ctx.HD("Subpart A—First subpart")
    subpart_title = builder.get_subpart_group_title(ctx.xml)
    assert subpart_title == 'Subpart A—First subpart'


def test_get_subpart_group_title_reserved():
    with XMLBuilder("SUBPART") as ctx:
        ctx.RESERVED("Subpart J [Reserved]")
    subpart_title = builder.get_subpart_group_title(ctx.xml)
    assert subpart_title == 'Subpart J [Reserved]'


def test_get_subpart_group_title_em():
    with XMLBuilder("SUBPART") as ctx:
        ctx.child_from_string(
            '<HD SOURCE="HED">Subpart B—<E T="0714">Partes</E> Review</HD>')
    subpart_title = builder.get_subpart_group_title(ctx.xml)
    assert subpart_title == 'Subpart B—Partes Review'
