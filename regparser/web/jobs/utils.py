from regparser.tasks import run_eregs_command
import django_rq
import settings


def queue_eregs_job(args, timeout=60*30, result_ttl=-1):
    """
    Adds an eRegs command to the Redis queue to be run asynchronously.

    Side effects
        Adds a job to the Redis queue; eventually runs a job that alters the
        data stored by the parser.

    :arg list args: The commands for the eRegs command.
    :arg int timeout: (Optional) How long (in seconds) the job should run
        before being considered "lost".
    :arg int result_ttl: (Optional) How long (in seconds) the key for the job
        result should be stored.

    :rtype: uuid4
    :returns: The UUID for the job.
    """
    return django_rq.enqueue(run_eregs_command, args, timeout=timeout,
                             result_ttl=result_ttl)


def delete_eregs_job(job_id):
    """
    Removes a job from the Redis queue.

    Side effects
        Removes a job from the Redis queue.

    :arg uuid4 job_id: The UUID for the job.

    :rtype: None
    :returns: None
    """
    queue = django_rq.get_queue()
    redis_job = queue.fetch_job(str(job_id))
    if redis_job:
        redis_job.delete()


def add_redis_data_to_job_data(job_data):
    """
    Retrieves status data about a job from the Redis queue and, if the job has
    failed and has logs, adds those logs to the job data.

    Impure
        Pulls information from the Redis queue.

    :arg list[ParsingJob] job_data: The jobs to have the status and log data
        added.

    :rtype: list[ParsingJob]
    :returns: Jobs with log data added to them.
    """
    queue = django_rq.get_queue()
    for job in job_data:
        redis_job = queue.fetch_job(str(job.job_id))
        if redis_job:
            job.status = redis_job.status
            if redis_job.meta.get("logs", False) and redis_job.is_failed:
                job.parser_errors = redis_job.meta["logs"]
            job.save()
    return job_data


def status_url(job_id):
    """
    We want to give users a URL for checking the status of a job.
    While I can't think of an exploit resulting from relying on the host data
    from the request if the request were spoofed, we'll be cautious and define
    the canonical host data ourselves.
    This helper function puts the lookup and the string manipulation in one
    place.

    Impure
        Pulls information from settings.

    :arg uuid4 job_id: The UUID of the job.

    :rtype: str
    :returns: The URL for checking on the status of the job.
    """
    hostname = getattr(settings, "CANONICAL_HOSTNAME", "")
    hostport = getattr(settings, "CANONICAL_PORT", "")
    if hostport:
        hostport = ":%s" % hostport
    return "%s%s/rp/job/%s/" % (hostname, hostport, job_id)
