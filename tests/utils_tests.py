from regparser import utils
from unittest import TestCase


class Utils(TestCase):
    def test_title_body_title_only(self):
        text = "This is some long, long title with no body"
        self.assertEqual((text, ""), utils.title_body(text))

    def test_title_body_normal_case(self):
        title = "This is a title"
        body = "Here is text that follows\nnewlines\n\n\nabout in the body"
        self.assertEqual((title, "\n" + body),
                         utils.title_body(title + "\n" + body))
