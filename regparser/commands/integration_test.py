import os
import sys

import click

from regparser.commands.pipeline import pipeline
from regparser.commands.compare_to import compare_to


targets = {
    # 'fec': {
    #     'title': 12,
    #     'parts': [1, 2, 4, 5, 6, 7, 8],
    #     'source': '',
    # },
    'atf': {
        'title': 27,
        'parts': [447, 478, 479, 555, 646],
        'source': 'https://atf-eregs.apps.cloud.gov/api',
    },
}


@click.command()
@click.argument('target')
@click.pass_context
def integration_test(ctx, target):
    config = targets[target]
    if any(build_and_compare(ctx, config, part) for part in config['parts']):
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
