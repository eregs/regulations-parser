""" doc2xml.py
Converts docx files representing a proposed rule into the type of XML we'd
expect from the Federal Register.

Executing: python doc2xml.py file.docx
    Writes XML to stdout

Installation:
    * Install libxml2 via a package manager
    * pip install -e git+https://github.com/savoirfairelinux/python-docx.git#egg=docx

Known limitations:
    * Ignores images, tables, equations, similar
    * Isn't aware of some bullets and other paragraph markers
    * Uses bold and italics (along with string matching) to determine what
      headers exist. If the docx uses custom style sheets instead, it won't
      work
    * Only processes the preamble data, not the CFR changes
"""     # noqa
from __future__ import print_function

import re
import sys
from itertools import tee

from lxml import etree

import docx

h2_re = re.compile('[A-Z]\.')
h3_re = re.compile('\d\d?\.')


def text_subel(root, tag, text, **attrs):
    """Util method for allowing a one-liner"""
    subel = etree.SubElement(root, tag, **attrs)
    subel.text = text
    return subel


def has_inline_label(par):
    return len(par.runs) > 1 and par.runs[0].bold


def is_heading(par, level):
    bold = all(run.bold for run in par.runs if run.text.strip())
    italics = all(run.italic for run in par.runs if run.text.strip())
    l2_marker = bool(h2_re.match(par.text.strip()))
    l3_marker = bool(h3_re.match(par.text.strip()))
    if level == 1:
        return bold
    elif level == 2:
        return italics and l2_marker
    elif level == 3:
        return l3_marker
    else:
        return False


class Builder(object):
    def __init__(self, paragraphs, xml_root):
        self._paragraphs = iter(paragraphs)     # always iterable
        self.xml_root = xml_root

    def takewhile(self, fn):
        while fn(self.head_p):
            yield next(self._paragraphs)

    def dropwhile(self, fn):
        while fn(self.head_p):
            next(self._paragraphs)
        return self

    def skip_header(self):
        def not_header(par):
            return not (par.text.strip() and par.runs[0].bold and
                        not any(c.isdigit() for c in par.text))
        self.dropwhile(not_header)
        return self

    def skip_whitespace(self):
        self.dropwhile(lambda p: not p.text.strip())
        return self

    @property
    def head_p(self):   # peek; non-destructive
        copy1, copy2 = tee(self._paragraphs)
        self._paragraphs = copy2
        return next(copy1)

    def consume_text(self):
        return next(self._paragraphs).text.strip()

    def intro_header(self, parent, start_p):
        label_to_tag = {
            'AGENCY': 'AGY',
            'ACTION': 'ACT',
            'SUMMARY': 'SUM',
            'DATES': 'DATES',
            'ADDRESSES': 'ADD',
            'FOR FURTHER INFORMATION CONTACT': 'FURINF',
        }

        label = next((l for l in label_to_tag if start_p.text.startswith(l)),
                     None)
        if label:
            sub_el = etree.SubElement(parent, label_to_tag[label])
            text_subel(sub_el, 'HD', label + ':', SOURCE='HED')
        else:
            sub_el = etree.SubElement(parent, "UNKNOWN")
            text_subel(sub_el, 'HD', start_p.runs[0].text, SOURCE='HED')
        return sub_el

    def intro_sections(self, preamb):
        intro = self.takewhile(
            lambda p: not p.text.startswith('SUPPLEMENTARY'))

        current_section = None

        for par in intro:
            if has_inline_label(par):
                current_section = self.intro_header(preamb, par)
                sub_p = etree.SubElement(current_section, 'P')
                text = ''.join(r.text for r in par.runs[1:])
                # strip the beginning colon as it's part of the label
                sub_p.text = text.lstrip(':').strip()
            elif current_section is not None:
                sub_p = etree.SubElement(current_section, 'P')
                sub_p.text = par.text.strip()

    def preamble(self):
        preamb = etree.SubElement(self.xml_root, 'PREAMB')

        text_subel(preamb, 'AGENCY', self.consume_text())
        self.skip_whitespace()

        if not self.head_p.text[:1].isdigit():
            text_subel(preamb, 'SUBAGENCY', self.consume_text())
            self.skip_whitespace()

        for tag in ('CFR', 'DEPDOC', 'RIN', 'SUBJECT'):
            text_subel(preamb, tag, self.consume_text())
            self.skip_whitespace()

        self.intro_sections(preamb)

        return self

    def suplinf(self):
        suplinf = etree.SubElement(self.xml_root, 'SUPLINF')
        text_subel(suplinf, 'HD', self.consume_text(), SOURCE='HED')

        self.dropwhile(lambda p: not is_heading(p, 1))
        non_cfr = self.takewhile(
            lambda p: not p.text.startswith('List of Subjects'))
        for par in non_cfr:
            if not par.text.strip():
                continue
            elif is_heading(par, 1):
                text_subel(suplinf, 'HD', par.text.strip(), SOURCE='HD1')
            elif is_heading(par, 2):
                text_subel(suplinf, 'HD', par.text.strip(), SOURCE='HD2')
            elif is_heading(par, 3):
                text_subel(suplinf, 'HD', par.text.strip(), SOURCE='HD3')
            else:
                text_subel(suplinf, 'P', par.text.strip())


def parse(filename):
    """Pulls out and prints some fields/paragraphs from an FR notice"""
    builder = Builder(docx.Document(filename).paragraphs,
                      etree.Element('PRORULE'))
    builder.skip_header()
    builder.preamble()
    builder.skip_whitespace()
    builder.suplinf()

    return builder.xml_root


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python doc2xml.py file.docx")    # noqa 
    else:
        print(etree.tounicode(parse(sys.argv[1]), pretty_print=True))   # noqa
