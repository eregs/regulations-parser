from regparser.web.settings.base import *  # noqa

REQUESTS_CACHE = {
    'backend': 'memory',
    'expire_after': 0   # immediately expire
}
