import os

import git

import settings
from . import ROOT


GIT_DIR = os.path.join(ROOT, 'xmls')


def sync():
    if os.path.isdir(GIT_DIR):
        repo = git.Repo.init(GIT_DIR)
    else:
        repo = git.Repo.clone_from(settings.XML_REPO, GIT_DIR)
    repo.remote().pull()
