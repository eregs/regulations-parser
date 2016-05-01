from regparser import search


def find_appendix_start(text):
    """Find the start of the appendix (e.g. Appendix A)"""
    return search.find_start(text, u'Appendix', ur'[A-Z] to Part')
