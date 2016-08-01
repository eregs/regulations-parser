import logging
import os
import time

from django.conf import settings as django_settings
import git

import settings


GIT_DIR = os.path.join(django_settings.EREGS_INDEX_ROOT, 'xmls')
logger = logging.getLogger(__name__)


def sync(ttl):
    """
    :param ttl: Time to cache last pull, in seconds. Pass `None` to force pull.
    """
    if os.path.isdir(GIT_DIR):
        logger.debug("Initting git repo at %s", GIT_DIR)
        repo = git.Repo.init(GIT_DIR)
    else:
        logger.debug("Clone git repo source: %s to: %s",
                     settings.XML_REPO, GIT_DIR)
        repo = git.Repo.clone_from(settings.XML_REPO, GIT_DIR)
    if ttl is None or should_pull(repo, ttl):
        logger.debug("Pulling git repo at %s", GIT_DIR)
        repo.remote().pull()


def should_pull(repo, ttl):
    try:
        stat = os.stat(os.path.join(repo.git_dir, 'FETCH_HEAD'))
        return (time.time() - stat.st_mtime) > ttl
    except OSError:
        return True
