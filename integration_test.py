#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import tarfile
import functools

import pip
import boto3
import click
import requests

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
    },
    'atf': {
        'title': 27,
        'parts': [447, 478, 479, 555, 646],
        'requirements': [
            '-e git+https://github.com/18F/atf-eregs.git#egg=atf-regparser&subdirectory=eregs_extensions',  # noqa
        ],
    },
}


def get_paths(target):
    return {
        'cached_archive': 'cached-{}.tar.gz'.format(target),
        'cached_dir': 'cached-{}'.format(target),
        'output_dir': 'output-{}'.format(target),
    }


def download(target):
    paths = get_paths(target)
    with open(paths['cached_archive'], 'wb') as fp:
        resp = requests.get(
            'https://{}.s3.amazonaws.com/{}'.format(
                os.getenv('BUCKET'),
                paths['cached_archive'],
            ),
            stream=True,
        )
        for chunk in resp.iter_content(chunk_size=1024):
            fp.write(chunk)
    with tarfile.open(paths['cached_archive']) as tar:
        tar.extractall()


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
def build(ctx, target):
    config = targets[target]
    paths = get_paths(target)
    for part in config['parts']:
        run_or_resolve(
            functools.partial(
                ctx.invoke,
                pipeline,
                cfr_title=config['title'],
                cfr_part=part,
                output=paths['output_dir'],
                only_latest=True,
            )
        )


@cli.command()
@click.argument('target')
@click.pass_context
def compare(ctx, target):
    download(target)
    config = targets[target]
    paths = get_paths(target)
    diffs = [
        ctx.invoke(
            compare_to,
            api_base=paths['cached_dir'],
            paths=[os.path.join(paths['output_dir'], 'regulation', str(part))],
            prompt=False,
        )
        for part in config['parts']
    ]
    if any(diffs):
        sys.exit(1)


@cli.command()
@click.argument('target')
def upload(target):
    paths = get_paths(target)
    with tarfile.open(paths['cached_archive'], 'w:gz') as tar:
        tar.add(paths['output_dir'], arcname=paths['cached_dir'])
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(os.getenv('BUCKET'))
    bucket.put_object(
        Key=paths['cached_archive'],
        Body=open(paths['cached_archive'], 'rb'),
    )


if __name__ == '__main__':
    cli()
