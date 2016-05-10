from datetime import date
from unittest import TestCase

from regparser.history import delays


class HistoryDelaysTests(TestCase):
    def test_delays_in_sentence(self):
        sent = "The effective date of 12 FR 501, 13 FR 999, and (13 FR 764) "
        sent += "has been delayed."
        self.assertEqual(
            delays.delays_in_sentence(sent),
            [delays.FRDelay(12, 501, None), delays.FRDelay(13, 999, None),
             delays.FRDelay(13, 764, None)])
        sent = "In 11 FR 123 we delayed the effective date"
        self.assertEqual(delays.delays_in_sentence(sent), [])
        sent = "The effective date of 9 FR 765 has been delayed until "
        sent += "January 7, 2008; rather I mean March 4 2008"
        self.assertEqual(
            delays.delays_in_sentence(sent),
            [delays.FRDelay(9, 765, date(2008, 3, 4))])
