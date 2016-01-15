"""Namespace for collecting the various types of markers"""

import itertools
import string

from regparser.utils import roman_nums


lower = (tuple(string.ascii_lowercase) +
         tuple(a+a for a in string.ascii_lowercase if a != 'i'))
upper = (tuple(string.ascii_uppercase) +
         tuple(a+a for a in string.ascii_uppercase))
ints = tuple(str(i) for i in range(1, 51))
roman = tuple(itertools.islice(roman_nums(), 0, 50))
upper_roman = tuple(r.upper() for r in roman)
em_ints = tuple('<E T="03">' + i + '</E>' for i in ints)
em_roman = tuple('<E T="03">' + i + '</E>' for i in roman)

# Distinction between types of stars as it indicates how much space they can
# occupy
STARS_TAG = 'STARS'
INLINE_STARS = '* * *'
stars = (STARS_TAG, INLINE_STARS)

# Account for paragraphs without a marker at all
MARKERLESS = 'MARKERLESS'
markerless = (MARKERLESS,)

types = [lower, upper, ints, roman, upper_roman, em_ints, em_roman, stars,
         markerless]
