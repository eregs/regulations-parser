import os

from django.conf import settings
import django_rq
import requests_cache


def http_client():
    config = settings.REQUESTS_CACHE
    if config.get('backend') == 'redis' and 'connection' not in config:
        config['connection'] = django_rq.get_connection()
    if config.get('backend') == 'sqlite':
        # Create parent directories, if needed
        parent_dir = os.path.dirname(config['cache_name'])
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)

    return requests_cache.CachedSession(**config)
