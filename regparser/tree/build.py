# vim: set encoding=utf-8
import re


def find_cfr_part(text):
    """Figure out what CFR this is referring to from the text."""
    for match in re.finditer(ur"^PART (\d+)[-—\w]", text):
        return int(match.group(1))
