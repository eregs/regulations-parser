# vim: set encoding=utf-8

from regparser.tree import reg_text
from unittest import TestCase


class DepthRegTextTest(TestCase):
    def test_find_next_section_start(self):
        text = u"\n\nSomething\n§ 205.3 thing\n\n§ 205.4 Something\n§ 203.19"
        self.assertEqual(12, reg_text.find_next_section_start(text, 205))
        self.assertEqual(None, reg_text.find_next_section_start(text, 204))
        self.assertEqual(45, reg_text.find_next_section_start(text, 203))

    def test_find_next_subpart_start(self):
        text = u"\n\nSomething\nSubpart A—Procedures for Application\n\n"
        self.assertEqual(12, reg_text.find_next_subpart_start(text))

    def test_next_subpart_offsets(self):
        """ Should get the start and end of each offset. """
        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection"
        text += u"\n\nSomething\nSubpart A—Procedures for Application\n\n"
        text += u"\n\nSomething else\nSubpart B—Model Forms for Application\n"
        self.assertEqual((56, 111), reg_text.next_subpart_offsets(text))

        text = u"\n\nSomething\nSubpart A—Application\nAppendix A to Part 201"
        self.assertEqual((12, 34), reg_text.next_subpart_offsets(text))

        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection"
        text += u"\n\nSomething\nubpart A—Procedures for Application\n\n"
        text += u"\n\nSomething else\nSubpart B—Model Forms for Application\n"
        self.assertEqual((110, 148), reg_text.next_subpart_offsets(text))

        text = u"ubpart A—First subpart\n"
        text += u"§ 201.20 dfds \n sdfds § 201.2 saddsa \n\n sdsadsa\n"
        text += u"\nSubpart B—Second subpart\n"
        text += u"§ 2015 dfds \n sdfds § 20132 saddsa \n\n sdsadsa\n"
        self.assertEqual((72, 143), reg_text.next_subpart_offsets(text))

        text = u"Supplement I\n\nSomething else\n"
        text += u"Subpart B—Model Forms for Application\n\n"
        self.assertEqual(None, reg_text.next_subpart_offsets(text))

        text = u"Appendix Q to Part 201\n\nSomething else\n"
        text += u"Subpart B—Model Forms for Application\n"
        self.assertEqual(None, reg_text.next_subpart_offsets(text))

    def test_next_section_offsets(self):
        """Should get the start and end of each section, even if it is
        followed by an Appendix or a supplement"""
        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n"
        text += u"§ 201.20 dfds \n sdfds § 201.2 saddsa \n\n sdsadsa"
        self.assertEqual((2, 45), reg_text.next_section_offsets(text, 201))

        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n"
        text += u"201.20 dfds \n sdfds § 201.2 saddsa \n\n sdsadsa"
        self.assertEqual((2, len(text)),
                         reg_text.next_section_offsets(text, 201))

        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \nAppendix A to Part 201"
        self.assertEqual((2, 29), reg_text.next_section_offsets(text, 201))

        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \nSupplement I"
        self.assertEqual((2, 29), reg_text.next_section_offsets(text, 201))

        text = u"Appendix A to Part 201\n\n§ 201.3 sdsa\nsdd dsdsadsa"
        self.assertEqual(None, reg_text.next_section_offsets(text, 201))

        text = u"Supplement I\n\n§ 201.3 sdsa\nsdd dsdsadsa"
        self.assertEqual(None, reg_text.next_section_offsets(text, 201))

    def test_sections(self):
        text = u"\n\n§ 201.3 sdsa\nsdd dsdsadsa \n asdsas\nSection\n"
        text += u"§ 201.20 dfds \n sdfds § 201.2 saddsa \n\n sdsadsa\n"
        text += u"Appendix A to Part 201 bssds \n sdsdsad \nsadad \ndsada"
        self.assertEqual([(2, 45), (45, 93)], reg_text.sections(text, 201))

    def test_subparts(self):
        text = u"Subpart A—First subpart\n"
        text += u"§ 201.20 dfds \n sdfds § 201.2 saddsa \n\n sdsadsa\n"
        text += u"\nSubpart B—Second subpart\n"
        text += u"§ 2015 dfds \n sdfds § 20132 saddsa \n\n sdsadsa\n"
        self.assertEqual([(0, 73), (73, 144)], reg_text.subparts(text))

    def test_subjgrp_label(self):
        # Single words:
        result = reg_text.subjgrp_label('Penalties', [])
        self.assertEqual('Pe', result)
        result = reg_text.subjgrp_label('Penalties', ['Pe'])
        self.assertEqual('Pe.', result)
        result = reg_text.subjgrp_label('Penalties', ['Pe', 'Pe.'])
        self.assertEqual('Pen', result)
        result = reg_text.subjgrp_label('Penalties', ['Pe', 'Pe.', 'Pen'])
        self.assertEqual('Pen.', result)
        result = reg_text.subjgrp_label('Pe', ['Pe', 'Pe.'])
        self.assertEqual('Pe-a', result)
        result = reg_text.subjgrp_label('Pe', ['Pe', 'Pe.', 'Pe-a'])
        self.assertEqual('Pe.-a', result)
        result = reg_text.subjgrp_label('Pe', ['Pe', 'Pe.', 'Pe-a', 'Pe.-a'])
        self.assertEqual('Pe-b', result)

        # Multiple words:
        result = reg_text.subjgrp_label('Change of Ownership', [])
        self.assertEqual('CoO', result)
        result = reg_text.subjgrp_label('Change of Ownership', ['CoO'])
        self.assertEqual('C.o.O.', result)
        result = reg_text.subjgrp_label('Change of Ownership',
                                        ['CoO', 'C.o.O.'])
        self.assertEqual('C_o_O', result)
        result = reg_text.subjgrp_label('Change of Ownership',
                                        ['CoO', 'C.o.O.', 'C-o-O', 'C_o_O'])
        self.assertEqual('ChofOw', result)
        result = reg_text.subjgrp_label(
            'Change of Ownership', ['CoO', 'C.o.O.', 'C_o_O', 'ChofOw'])
        self.assertEqual('Ch.of.Ow.', result)
        result = reg_text.subjgrp_label(
            'Change of Ownership',
            ['CoO', 'C.o.O.', 'C_o_O', 'ChofOw', 'Ch.of.Ow.'])
        self.assertEqual('Ch_of_Ow', result)
        result = reg_text.subjgrp_label(
            'C o O', ['CoO', 'C.o.O.', 'C_o_O'])
        self.assertEqual('CoO-a', result)
