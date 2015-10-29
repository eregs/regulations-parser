import json
import os
import shutil
import tempfile

import click
from json_delta import udiff
import requests
import requests_cache

from regparser.commands.write_to import write_to


def files_to_compare(tmppath, relevant_paths=None):
    """List of all file names we should care about comparing. Filters out any
    paths which do not begin with a string in relevant_paths"""
    relevant_paths = relevant_paths or ['']
    file_names = [os.path.join(dir_path, file_name)
                  for dir_path, _, file_names in os.walk(tmppath)
                  for file_name in file_names]
    # strip the tempdir info
    file_names = [file_name[len(tmppath)+1:] for file_name in file_names]
    matches_a_path = lambda f: any(f.startswith(p) for p in relevant_paths)

    return filter(matches_a_path, file_names)


def compare(local_path, remote_url):
    """Downloads and compares a local JSON file with a remote one. If there is
    a difference, notifies the user and prompts them if they want to see the
    diff"""
    remote_response = requests.get(remote_url)
    if remote_response.status_code == 404:
        click.echo("Nonexistent: " + remote_url)
    else:
        remote = remote_response.json()
        with open(local_path) as f:
            local = json.load(f)

        if remote != local:
            click.echo("Content differs: {} {}".format(local_path, remote_url))
            if click.confirm("Show diff?"):
                map(click.echo, udiff(remote, local))


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.argument('api_base')
@click.argument('path', nargs=-1)
@click.pass_context
def compare_to(ctx, cfr_title, cfr_part, api_base, path):
    """Compare local JSON to a remote server. This is useful for verifying
    changes to the parser.

    API_BASE is the uri of the root of the API. Use what would be the last
    parameter in the `write_to` command.

    PATH parameters will filter the files we're trying to compare. For
    example, if we only want to see the difference between trees, one of the
    PATH parameters should be "regulation".
    """
    if not api_base.endswith("/"):
        api_base += "/"

    tmppath = tempfile.mkdtemp()
    ctx.invoke(write_to, cfr_title=cfr_title, cfr_part=cfr_part,
               output=tmppath)

    # @todo: ugly to uninstall the cache after installing it in eregs.py.
    # Remove the globalness
    requests_cache.uninstall_cache()

    for file_name in files_to_compare(tmppath, path or ['']):
        local_name = os.path.join(tmppath, file_name)
        remote_name = api_base + file_name.replace(os.path.sep, "/")
        compare(local_name, remote_name)
    shutil.rmtree(tmppath)
