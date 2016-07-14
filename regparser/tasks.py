import logging

import django_rq
from rq import get_current_job
from six import StringIO

from regparser.web.management.commands import eregs


def run_eregs_command(eregs_args):
    """Run `eregs *eregs_args`, capturing all of the logs and storing them in
    Redis"""
    log = StringIO()
    logger = logging.getLogger('regparser')
    log_handler = logging.StreamHandler(log)

    logger.propagate = False
    logger.addHandler(log_handler)

    try:
        context = eregs.cli.make_context('eregs', args=list(eregs_args))
        eregs.cli.invoke(context)
    finally:
        log_handler.flush()
        # Recreating the connection due to a bug in rq:
        # https://github.com/nvie/rq/issues/479
        conn = django_rq.get_connection()
        job = get_current_job(conn)
        job.meta['logs'] = log.getvalue()
        job.save()
        logger.removeHandler(log_handler)
