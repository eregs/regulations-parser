import codecs
import sys

import click

from regparser.citations import cfr_citations


@click.command()
@click.argument('input_files', nargs=-1, type=click.File('rb'))
@click.option('--unique/--no-unique', default=False,
              help='Remove duplicate citations')
def citations(input_files, unique):
    """Find all CFR citations in a file (or stdin)"""
    if not input_files:
        input_files = [codecs.getreader('utf8')(sys.stdin)]
    for file_ in input_files:
        text = file_.read()
        cits = cfr_citations(text, include_fill=True)
        if unique:
            labels = {citation.label for citation in cits}
            for label in sorted(labels):
                click.echo(label)
        else:
            for citation in sorted(cits, key=lambda c: c.start):
                click.echo(u"{0}: {1}\n".format(
                    text[citation.start:citation.end], citation.label))
