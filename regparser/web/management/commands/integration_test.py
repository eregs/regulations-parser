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


@attr.attrs(slots=True, frozen=True)
class Target(object):
    title = attr.attrib()
    parts = attr.attrib()
    reqs = attr.attrib(default=attr.Factory(dict))
    flags = attr.attrib(default=None)


targets = {
    'fec': Target(
        title=11,
        parts=(
            [1, 2, 4, 5, 6, 7, 8] +
            list(range(100, 117)) + [200, 201, 300] +
            list(range(9001, 9009)) + [9012] + list(range(9031, 9040)) +
            [9405, 9407, 9409, 9410, 9411, 9420, 9428, 9430]
        ),
        reqs={
            'fec_regparser': '-e git+https://github.com/18F/fec-eregs.git#egg=fec_regparser&subdirectory=eregs_extensions',  # noqa
        },
        flags='--only-latest'
    ),
    'atf': Target(
        title=27,
        parts=[447, 478, 479, 555, 646],
        reqs={
            'atf_regparser': '-e git+https://github.com/18F/atf-eregs.git#egg=atf_regparser&subdirectory=eregs_extensions',  # noqa
        },
    ),
    'epa': Target(
        title=40,
        parts=[262, 263, 264, 265, 271],
        reqs={
            'epa_regparser': '-e git+https://github.com/18F/epa-notice.git#egg=epa_regparser&subdirectory=eregs_extensions',  # noqa
        },
        flags='--only-latest'
    ),
}


_ground_truth = functools.partial(os.path.join, 'tests', 'integration-data')
_current_output = 'output-{0}'.format


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
    config = targets[target]

    for part in config.parts:
        args = ['pipeline', str(config.title), str(part),
                _current_output(target)]
        if config.flags:
            args.append(config.flags)
        eregs_cli(*args)


@integration_test.command()
@click.argument('target')
@click.pass_context
def compare(ctx, target):
    diffs = ctx.invoke(
        compare_to,
        api_base=_ground_truth(target),
        paths=[_current_output(target)],
        prompt=False,
    )
    if diffs:
        sys.exit(1)
