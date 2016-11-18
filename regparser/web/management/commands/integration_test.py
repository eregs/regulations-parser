"""
Integration tests verifying that revisions to the parser don't change previous
results from known agency users. On each pull request, parse regulations from
known users and compare against the cached ground truth parse; if different,
fail the build. On passing builds against master, parse regulations and upload
to cache as the current ground truth.
"""

import os
import sys
import tarfile

import boto3
import djclick as click
import pip
import requests

from regparser.commands.compare_to import compare_to
from regparser.web.management.commands.eregs import cli as eregs_cli


targets = {
    'fec': {
        'title': 11,
        'parts': (
            [1, 2, 4, 5, 6, 7, 8] +
            list(range(100, 117)) + [200, 201, 300] +
            list(range(9001, 9009)) + [9012] + list(range(9031, 9040)) +
            [9405, 9407, 9409, 9410, 9411, 9420, 9428, 9430]
        ),
    },
    'atf': {
        'title': 27,
        'parts': [447, 478, 479, 555, 646],
        'requirements': {
            'atf_regparser': '-e git+https://github.com/18F/atf-eregs.git#egg=atf_regparser&subdirectory=eregs_extensions',  # noqa
        },
    },
    'epa': {
        'title': 40,
        'parts': [262, 263, 264, 265, 271],
        'requirements': {
            'epa_regparser': '-e git+https://github.com/18F/epa-notice.git#egg=epa_regparser&subdirectory=eregs_extensions',  # noqa
        },
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
def integration_test():
    pass


@integration_test.command()
@click.argument('target')
def install(target):
    config = targets[target]
    for requirement in config.get('requirements', {}).values():
        pip.main(['install', '--upgrade'] + requirement.split())


@integration_test.command()
def uninstall():
    for config in targets.values():
        for package in config.get('requirements', {}).keys():
            pip.main(['uninstall', '--yes', package])


@integration_test.command()
@click.argument('target')
def build(target):
    config = targets[target]
    paths = get_paths(target)

    for part in config['parts']:
        eregs_cli('pipeline', str(config['title']), str(part),
                  paths['output_dir'], '--only-latest')


@integration_test.command()
@click.argument('target')
@click.pass_context
def compare(ctx, target):
    download(target)
    paths = get_paths(target)
    diffs = ctx.invoke(
        compare_to,
        api_base=paths['cached_dir'],
        paths=[paths['output_dir']],
        prompt=False,
    )
    if diffs:
        sys.exit(1)


@integration_test.command()
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
