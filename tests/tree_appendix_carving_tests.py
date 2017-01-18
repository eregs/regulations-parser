# vim: set encoding=utf-8
from unittest import TestCase

from regparser.tree.appendix import carving


class DepthAppendixCarvingTest(TestCase):

    def test_find_appendix_start(self):
        text = "Some \nAppendix C to Part 111 Other\n\n "
        text += "Thing Appendix A to Part 111"
        text += "\nAppendix B to Part 111"
        self.assertEqual(6, carving.find_appendix_start(text))
        self.assertEqual(59, carving.find_appendix_start(text[7:]))
        self.assertEqual(None, carving.find_appendix_start(text[7 + 60:]))
