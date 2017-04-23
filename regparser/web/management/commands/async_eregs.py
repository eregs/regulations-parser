from argparse import RawTextHelpFormatter

import django_rq
from django.core.management.base import BaseCommand
from rq import registry
from rq.queue import FailedQueue

from regparser.tasks import run_eregs_command

_OPTIONS = ('cfr_title', 'cfr_part', 'xml-ttl')
_FLAGS = ('only-latest', 'unique', 'prompt')


def argparse_to_click(eregs_args, **kwargs):
    """Django uses argparse for parameters, but we use click. Hack a
    conversion between the two"""
    args = list(eregs_args)
    for option in _OPTIONS:
        underscored = option.replace('-', '_')
        if kwargs.get(underscored):
            args.append('--' + option)
            args.append(kwargs[underscored])
    for flag in _FLAGS:
        underscored = flag.replace('-', '_')
        if kwargs.get(underscored):
            args.append('--' + flag)
    return args


def _print(write_fn, job):
    logs = job.meta.get('logs', '')
    log_length = len(logs.split('\n'))
    write_fn("\t{0}\n\t\tLogs:{1}".format(job, log_length))


def show_stats(write_fn):
    """Print some metrics to stdout"""
    queue = django_rq.get_queue()
    conn = django_rq.get_connection()

    write_fn("Queued:")
    for job in queue.jobs:
        _print(write_fn, job)

    write_fn("Started:")
    for job_id in registry.StartedJobRegistry(connection=conn).get_job_ids():
        _print(write_fn, queue.fetch_job(job_id))

    write_fn("Finished:")
    for job_id in registry.FinishedJobRegistry(connection=conn).get_job_ids():
        _print(write_fn, queue.fetch_job(job_id))

    write_fn("Failed:")
    for job in FailedQueue(connection=conn).jobs:
        _print(write_fn, job)
        for line in job.exc_info.split('\n'):
            write_fn("\t\t" + line)


class Command(BaseCommand):
    help = (    # noqa
        """
        Asynchronous `eregs` commands. To run,
        1. start redis. For example, with docker:
            docker run -p 6379:6379 -d redis
        2. start a worker process
            python manage.py rqworker
        3. run an asynchronous command
            python manage.py async_eregs pipeline 27 479 async_output_dir
        4. check the status of your jobs:
            python manage.py async_eregs    # no parameters
        """
    )

    def add_arguments(self, parser):
        parser.formatter_class = RawTextHelpFormatter
        parser.add_argument('eregs_args', nargs='*')
        for option in _OPTIONS:
            parser.add_argument('--' + option)
        for flag in _FLAGS:
            parser.add_argument('--' + flag, action='store_const', const=True)

    def handle(self, *args, **kwargs):
        eregs_args = argparse_to_click(**kwargs)
        if not eregs_args:
            show_stats(self.stdout.write)
        else:
            job = django_rq.enqueue(run_eregs_command, eregs_args,
                                    # Run for at most half an hour
                                    # Don't delete successes
                                    timeout=60 * 30, result_ttl=-1)
            self.stdout.write("OK: {0}".format(job))
