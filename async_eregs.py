"""
Asynchronous `eregs` commands. To run,
    1. install `rq`
    2. start redis. For example, with docker:
        docker run -p 6379 -d redis
    3. start a worker process
        rq worker
        # use the --url form if needed:
        # rq worker --url redis://hostname:port/db
    4. run an asynchronous command
        python async_eregs.py pipeline 27 479 async_output_dir
        # use --host, --port, --db if needed
        # python async_eregs.py --host example.com pipeline ...
    5. check the status of your jobs:
        python async_eregs.py   # no parameters other than host, port, db
"""

import click
from rq import Queue, registry
from rq.queue import FailedQueue
from redis import StrictRedis

from regparser.tasks import run_eregs_command


def _print(job):
    log_length = len(job.meta.get('logs', ''))
    click.echo("\t({}){}".format(log_length, job))


def show_stats(conn):
    """Print some metrics to stdout"""
    queue = Queue(connection=conn)
    click.echo("Queued:")
    for job in queue.jobs:
        _print(job)

    click.echo("Started:")
    for job_id in registry.StartedJobRegistry(connection=conn).get_job_ids():
        _print(queue.fetch_job(job_id))

    click.echo("Finished:")
    for job_id in registry.FinishedJobRegistry(connection=conn).get_job_ids():
        _print(queue.fetch_job(job_id))

    click.echo("Failed:")
    for job in FailedQueue(connection=conn).jobs:
        _print(job)


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.option('--host', default='localhost', help='Redis host')
@click.option('--port', default=6379, help='Redis port')
@click.option('--db', default=0, help='Redis db')
@click.argument('eregs_args', nargs=-1, type=click.UNPROCESSED)
def main(host, port, db, eregs_args):
    """Run an eregs command asynchronously."""
    eregs_args = list(eregs_args)
    conn = StrictRedis(host=host, port=port, db=db)
    if not eregs_args:
        show_stats(conn)
    else:
        queue = Queue(connection=conn)
        # Can't directly use the above context as it doesn't pickle well
        queue.enqueue(run_eregs_command, eregs_args, host, port, db,
                      # Run for at most half an hour, don't delete successes
                      timeout=60*30, result_ttl=-1)
        click.echo("OK")


if __name__ == '__main__':
    main()
