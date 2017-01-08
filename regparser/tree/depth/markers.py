"""Namespace for collecting the various types of markers"""
import string

from roman import toRoman


def emphasize(marker):
    """The final depth levels for regulation text are emphasized, so we keep
    their <E> tags to distinguish them from previous levels. This function
    will wrap a marker in an <E> tag"""
    marker_plain = deemphasize(marker)
    return u'<E T="03">{0}</E>'.format(marker_plain)


def deemphasize(marker):
    """Though the knowledge of emphasis is helpful for determining depth, it
    is _unhelpful_ in other scenarios, where we only care about the plain
    text. This function removes <E> tags"""
    return marker.replace('<E T="03">', '').replace('</E>', '')


lower = (tuple(string.ascii_lowercase) +
         tuple(a + a for a in string.ascii_lowercase if a != 'i'))
upper = (tuple(string.ascii_uppercase) +
         tuple(a + a for a in string.ascii_uppercase))
ints = tuple(str(i) for i in range(1, 999))
upper_roman = tuple(toRoman(i) for i in range(1, 50))
roman = tuple(r.lower() for r in upper_roman)
em_ints = tuple(emphasize(i) for i in ints)
em_roman = tuple(emphasize(i) for i in roman)


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
