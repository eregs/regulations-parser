#!/usr/bin/env python
# encoding: utf-8

import os
import sys

import pip
import click

from eregs import run_or_resolve
from regparser.commands.pipeline import pipeline
from regparser.commands.compare_to import compare_to


targets = {
    'fec': {
        'title': 11,
        'parts': (
            [1, 2, 4, 5, 6, 7, 8] +
            range(100, 117) + [200, 201, 300] +
            range(9001, 9009) + [9012] + range(9031, 9040) +
            [9405, 9407, 9409, 9410, 9411, 9420, 9428, 9430]
        ),
        'source': 'https://fec-eregs.apps.cloud.gov/api',
    },
    'atf': {
        'title': 27,
        'parts': [447, 478, 479, 555, 646],
        'source': 'https://atf-eregs.apps.cloud.gov/api',
        'requirements': [
            '-e git+https://github.com/18F/atf-eregs.git#egg=atf-regparser&subdirectory=eregs_extensions',  # noqa
        ],
    },
}


@click.group()
def cli():
    pass


@cli.command()
@click.argument('target')
@click.pass_context
def install(ctx, target):
    config = targets[target]
    for requirement in config.get('requirements', []):
        pip.main(['install', '--upgrade'] + requirement.split())


@cli.command()
@click.argument('target')
@click.pass_context
def test(ctx, target):
    config = targets[target]
    if any([build_and_compare(ctx, config, part) for part in config['parts']]):
        sys.exit(1)


def build_and_compare(ctx, config, part):
    ctx.invoke(
        pipeline,
        cfr_title=config['title'],
        cfr_part=part,
        output='output',
        only_latest=True,
    )
    return ctx.invoke(
        compare_to,
        api_base=config['source'],
        paths=[os.path.join('output', 'regulation', str(part))],
        prompt=False,
    )


if __name__ == '__main__':
    run_or_resolve(cli)
