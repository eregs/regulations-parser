import json
import logging
import os

import click
from json_delta import udiff
import requests
import requests_cache


def local_and_remote_generator(api_base, paths):
    """Find all local files in `paths` and pair them with the appropriate
    remote file (prefixing with api_base). As the local files could be at any
    position in the file system, we back out directories until we hit one of
    the four root resource types (diff, layer, notice, regulation)"""
    local_names = [path for path in paths if os.path.isfile(path)]
    # this won't duplicate the previous line as it'll only add files in dirs
    local_names.extend(os.path.join(dirpath, filename)
                       for path in paths
                       for dirpath, _, filenames in os.walk(path)
                       for filename in filenames)
    for local_name in local_names:
        dirname, basename = os.path.split(local_name)
        reversed_suffix = [basename]
        # these are the four root resource types
        while basename not in ('diff', 'layer', 'notice', 'regulation'):
            dirname, basename = os.path.split(dirname)
            reversed_suffix.append(basename)
        remote_name = api_base + '/'.join(reversed(reversed_suffix))
        yield (local_name, remote_name)


def compare(local_path, remote_url, prompt):
    """Downloads and compares a local JSON file with a remote one. If there is
    a difference, notifies the user and prompts them if they want to see the
    diff"""
    remote_response = requests.get(remote_url)
    if remote_response.status_code == 404:
        logging.warn("Nonexistent: %s", remote_url)
    else:
        remote = remote_response.json()
        with open(local_path) as f:
            local = json.load(f)

        if remote != local:
            click.echo("Content differs: {} {}".format(local_path, remote_url))
            if not prompt or click.confirm("Show diff?"):
                diff = udiff(remote, local)
                diffs_str = '\n'.join(diff)
                (click.echo_via_pager if prompt else click.echo)(diffs_str)
                return diff


@click.command()
@click.argument('api_base')
@click.argument('paths', nargs=-1, required=True,
                type=click.Path(exists=True, resolve_path=True))
@click.option('--prompt/--no-prompt', default=True)
@click.pass_context
def compare_to(ctx, api_base, paths, prompt):
    """Compare local JSON to a remote server. This is useful for verifying
    changes to the parser.

    API_BASE is the uri of the root of the API. Use what would be the last
    parameter in the `write_to` command.

    PATH parameters indicate specific files or directories to use when
    comparing. For example, use `/some/path/to/regulation/555` to compare all
    versions of 555. Glob syntax works if your shell supports it"""
    if not api_base.endswith("/"):
        api_base += "/"

    # @todo: ugly to uninstall the cache after installing it in eregs.py.
    # Remove the globalness
    requests_cache.uninstall_cache()

    pairs = local_and_remote_generator(api_base, paths)
    return any(compare(local, remote, prompt) for local, remote in pairs)
