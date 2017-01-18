import django_rq
from django.conf import settings as django_settings
from django.core.mail import get_connection, send_mail

import settings
from regparser.tasks import run_eregs_command

eregs_site_api_url = getattr(settings, "EREGS_SITE_API_URL")


def queue_eregs_job(args, timeout=60 * 30, result_ttl=-1):
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


def send_notification_email(email_address, status_url):
    backend = django_settings.EMAIL_BACKEND
    connection = get_connection(backend=backend)
    send_mail(status_url, "Job finished at {0}".format(status_url),
              "notifications@18F.gov", [email_address], connection=connection)


def queue_notification_email(job, status_url, email_address):
    return django_rq.enqueue(send_notification_email, email_address,
                             status_url, depends_on=job)


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


def get_host():
    """
    We want to provide users with status URLs, and so need host:port.
    While I can't think of an exploit resulting from relying on the host data
    from the request if the request were spoofed, we'll be cautious and define
    the canonical host data ourselves.
    This helper function puts the lookup and the string manipulation in one
    place.

    Impure
        Pulls information from settings.

    :rtype: str
    :returns: The URL for host in the form host:port, for example:
        http://domain.tld:2323

        Note that the schema is not supplied (we assume it's included in the
        string provided to settings) and no trailing slash is provided.

        We assume that the port from setigns is the bare number, with no
        trailing colon, so we add that here.
    """
    hostname = getattr(settings, "CANONICAL_HOSTNAME", "")
    hostport = getattr(settings, "CANONICAL_PORT", "")
    if hostport and hostport not in ("80", "443"):
        hostport = ":{0}".format(hostport)
    elif hostport in ("80", "443"):
        hostport = ""
    return "{0}{1}".format(hostname, hostport)


def create_status_url(job_id, sub_path=""):
    """
    Returns a URL for checking the status of a job.

    Impure
        Via get_host(), pulls information from settings.

    :arg uuid4 job_id: The UUID of the job.
    :arg str sub_path: The part of the path indicating the type of job. Must
        include a trailing slash.

    :rtype: str
    :returns: The URL for checking on the status of the job.
    """
    if sub_path and not sub_path.endswith("/"):
        raise ValueError
    host = get_host()
    return "{0}/rp/jobs/{1}{2}/".format(host, sub_path, job_id)


def file_url(file_hash):
    """
    Returns a URL for retrieving an uploaded file.

    Impure
        Via get_host(), pulls information from settings.

    :arg str file_hash: The MD5 hexstring of the file contents.

    :rtype: str
    :returns: The URL for checking on the status of the job.
    """
    host = get_host()
    return "{0}/rp/jobs/files/{1}/".format(host, file_hash)
