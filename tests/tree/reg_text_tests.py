# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from regparser.tree import reg_text


def test_find_next_section_start():
    text = "\n\nSomething\n§ 205.3 thing\n\n§ 205.4 Something\n§ 203.19"
    assert reg_text.find_next_section_start(text, 203) == 45
    assert reg_text.find_next_section_start(text, 204) is None
    assert reg_text.find_next_section_start(text, 205) == 12


def test_find_next_subpart_start():
    text = "\n\nSomething\nSubpart A—Procedures for Application\n\n"
    assert reg_text.find_next_subpart_start(text) == 12


@pytest.mark.parametrize('text,expected', [
    ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n\nSomething\n"
     "Subpart A—Procedures for Application\n\n\n\nSomething else\nSubpart "
     "B—Model Forms for Application\n", (56, 111)),
    ("\n\nSomething\nSubpart A—Application\nAppendix A to Part 201", (12, 34)),
    ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n\nSomething\n"
     "ubpart A—Procedures for Application\n\n\n\nSomething else\nSubpart "
     "B—Model Forms for Application\n", (110, 148)),
    ("ubpart A—First subpart\n§ 201.20 dfds \n sdfds § 201.2 saddsa \n\n "
     "sdsadsa\n\nSubpart B—Second subpart\n§ 2015 dfds \n sdfds § 20132 "
     "saddsa \n\n sdsadsa\n", (72, 143)),
    ("Supplement I\n\nSomething else\nSubpart B—Model Forms for Application"
     "\n\n", None),
    ("Appendix Q to Part 201\n\nSomething else\nSubpart B—Model Forms for "
     "Application\n", None)
])
def test_next_subpart_offsets(text, expected):
    """ Should get the start and end of each offset. """
    assert reg_text.next_subpart_offsets(text) == expected


@pytest.mark.parametrize('text,expected', [
    ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n§ 201.20 dfds \n "
     "sdfds § 201.2 saddsa \n\n sdsadsa", (2, 45)),
    ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n201.20 dfds \n "
     "sdfds § 201.2 saddsa \n\n sdsadsa", (2, 90)),
    ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \nAppendix A to Part 201", (2, 29)),
    ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \nSupplement I", (2, 29)),
    ("Appendix A to Part 201\n\n§ 201.3 sdsa\nsdd dsdsadsa", None),
    ("Supplement I\n\n§ 201.3 sdsa\nsdd dsdsadsa", None)
])
def test_next_section_offsets(text, expected):
    """Should get the start and end of each section, even if it is
    followed by an Appendix or a supplement"""
    assert reg_text.next_section_offsets(text, 201) == expected


def test_sections():
    text = ("\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n§ 201.20 dfds "
            "\n sdfds § 201.2 saddsa \n\n sdsadsa\nAppendix A to Part 201 "
            "bssds \n sdsdsad \nsadad \ndsada")
    assert [(2, 45), (45, 93)] == reg_text.sections(text, 201)


def test_subparts():
    text = ("Subpart A—First subpart\n§ 201.20 dfds \n sdfds § 201.2 saddsa "
            "\n\n sdsadsa\n\nSubpart B—Second subpart\n§ 2015 dfds \n sdfds "
            "§ 20132 saddsa \n\n sdsadsa\n")
    assert [(0, 73), (73, 144)] == reg_text.subparts(text)


@pytest.mark.parametrize('text,existing,expected', [
    # Single words:
    ('Penalties', [], 'Pe'),
    ('Penalties', ['Pe'], 'Pe.'),
    ('Penalties', ['Pe', 'Pe.'], 'Pen'),
    ('Penalties', ['Pe', 'Pe.', 'Pen'], 'Pen.'),
    ('Pe', ['Pe', 'Pe.'], 'Pe-a'),
    ('Pe', ['Pe', 'Pe.', 'Pe-a'], 'Pe.-a'),
    ('Pe', ['Pe', 'Pe.', 'Pe-a', 'Pe.-a'], 'Pe-b'),
    # Multiple words:
    ('Change of Ownership', [], 'CoO'),
    ('Change of Ownership', ['CoO'], 'C.o.O.'),
    ('Change of Ownership', ['CoO', 'C.o.O.'], 'C_o_O'),
    ('Change of Ownership', ['CoO', 'C.o.O.', 'C-o-O', 'C_o_O'], 'ChofOw'),
    ('Change of Ownership', ['CoO', 'C.o.O.', 'C_o_O', 'ChofOw'], 'Ch.of.Ow.'),
    ('Change of Ownership', ['CoO', 'C.o.O.', 'C_o_O', 'ChofOw', 'Ch.of.Ow.'],
     'Ch_of_Ow'),
    ('C o O', ['CoO', 'C.o.O.', 'C_o_O'], 'CoO-a'),
])
def test_subjgrp_label(text, existing, expected):
    assert reg_text.subjgrp_label(text, existing) == expected
