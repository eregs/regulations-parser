from django.conf import settings
import django_rq
import requests_cache


def http_client():
    config = settings.REQUESTS_CACHE
    if config.get('backend') == 'redis' and 'connection' not in config:
        config['connection'] = django_rq.get_connection()

    return requests_cache.CachedSession(**config)
