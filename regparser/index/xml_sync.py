import os
import time

import git

import settings
from . import ROOT


GIT_DIR = os.path.join(ROOT, 'xmls')


def sync(ttl):
    """
    :param ttl: Time to cache last pull, in seconds. Pass `None` to force pull.
    """
    if os.path.isdir(GIT_DIR):
        repo = git.Repo.init(GIT_DIR)
    else:
        repo = git.Repo.clone_from(settings.XML_REPO, GIT_DIR)
    if ttl is None or should_pull(repo, ttl):
        repo.remote().pull()


def should_pull(repo, ttl):
    try:
        stat = os.stat(os.path.join(repo.git_dir, 'FETCH_HEAD'))
        return (time.time() - stat.st_mtime) > ttl
    except OSError:
        return True
