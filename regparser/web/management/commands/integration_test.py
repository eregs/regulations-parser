"""
Integration tests verifying that revisions to the parser don't change previous
results from known agency users. On each pull request, parse regulations from
known users and compare against the cached ground truth parse; if different,
fail the build. On passing builds against master, parse regulations and upload
to cache as the current ground truth.
"""

import functools
import os.path
import sys

import attr
import djclick as click
import pip

from regparser.commands.compare_to import compare_to
from regparser.web.management.commands.eregs import cli as eregs_cli

_output_dir = functools.partial(os.path.join, 'output')
_ground_truth = functools.partial(os.path.join, 'tests', 'integration-data')


@attr.attrs(slots=True, frozen=True)
class Target(object):
    reqs = attr.attrib(default=attr.Factory(dict))
    script = attr.attrib(default=attr.Factory(list))


def cmd(*args):
    return tuple(str(a) for a in args)


fec_parts = [1, 2, 4, 5, 6, 7, 8] + \
    list(range(100, 117)) + \
    [200, 201, 300] + \
    list(range(9001, 9009)) + \
    [9012] + \
    list(range(9031, 9040)) + \
    [9405, 9407, 9409, 9410, 9411, 9420, 9428, 9430]
targets = {
    'fec': Target(
        reqs=dict(fec_regparser=(
            '-e git+https://github.com/18F/fec-eregs.git#egg=fec_regparser'
            '&subdirectory=eregs_extensions'
        )),
        script=[
            cmd('annual_version', 11, p, '--year', 2016) for p in fec_parts
        ] + [cmd('layers')] + [
            cmd('diffs', 11, part) for part in fec_parts
        ] + [cmd('write_to', _output_dir('fec'))]
    ),
    'atf': Target(
        reqs=dict(atf_regparser=(
            '-e git+https://github.com/18F/atf-eregs.git#egg=atf_regparser'
            '&subdirectory=eregs_extensions'
        )),
        script=[
            cmd('pipeline', 27, part, _output_dir('atf'))
            for part in (447, 478, 479, 555, 646)
        ]
    ),
    'epa': Target(
        reqs=dict(epa_regparser=(
            '-e git+https://github.com/18F/epa-notice.git#egg=epa_regparser'
            '&subdirectory=eregs_extensions'
        )),
        script=[
            cmd('annual_version', 40, part, '--year', 2015)
            for part in (262, 263, 264, 265, 271)
        ] + [cmd('layers')] + [
            cmd('diffs', 40, part) for part in (262, 263, 264, 265, 271)
        ] + [cmd('write_to', _output_dir('epa'))]
    ),
    'uspto': Target(
        script=[
            cmd('full_issuance', 37, 42, '2012-17900'),
            cmd('pipeline', 37, 42, _output_dir('uspto'))
        ]
    ),
}


@click.group()
def integration_test():
    pass


@integration_test.command()
@click.argument('target')
def install(target):
    config = targets[target]
    for requirement in config.reqs.values():
        pip.main(['install', '--upgrade'] + requirement.split())


@integration_test.command()
def uninstall():
    for config in targets.values():
        for package in config.reqs.keys():
            pip.main(['uninstall', '--yes', package])


@integration_test.command()
@click.argument('target')
def build(target):
    for line in targets[target].script:
        eregs_cli(*line)


@integration_test.command()
@click.argument('target')
@click.pass_context
def compare(ctx, target):
    diffs = ctx.invoke(
        compare_to,
        api_base=_ground_truth(target),
        paths=[_output_dir(target)],
        prompt=False,
    )
    if diffs:
        sys.exit(1)
