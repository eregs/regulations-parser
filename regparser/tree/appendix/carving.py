from __future__ import unicode_literals

from regparser import search


def find_appendix_start(text):
    """Find the start of the appendix (e.g. Appendix A)"""
    return search.find_start(text, 'Appendix', r'[A-Z] to Part')
