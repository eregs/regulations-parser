import os

import requests_cache   # @todo - replace with cache control

from . import ROOT


PATH = os.path.join(ROOT, 'http_cache.sqlite')


def install():
    if not os.path.exists(ROOT):
        os.makedirs(ROOT)
    requests_cache.install_cache(PATH, expire_after=60*60*24*3)  # 3 days
