import os

from regparser.web.settings.base import *  # noqa

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = False

# @todo - cloud.gov stuffs for ALLOWED_HOSTS, CACHES

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

REQUESTS_CACHE.update(backend='redis', cache_name='http_cache')  # noqa
