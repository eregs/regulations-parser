from django.db import models

job_status_pairs = (
    ("complete", "complete"),
    ("complete_with_errors", "complete_with_errors"),
    ("failed", "failed"),
    ("in_progress", "in_progress"),
    ("received", "received")
)
job_status_values = tuple(j[0] for j in job_status_pairs)


class ParsingJob(models.Model):

    class Meta:
        abstract = True

    created = models.DateTimeField(auto_now_add=True)
    clear_cache = models.BooleanField(default=False)
    destination = models.URLField(max_length=2000)
    notification_email = models.EmailField(blank="True", max_length=254)
    job_id = models.UUIDField(default=None, null=True)
    use_uploaded_metadata = models.UUIDField(default=None, null=True)
    use_uploaded_regulation = models.UUIDField(default=None, null=True)

    parser_errors = models.TextField(blank=True)
    regulation_url = models.URLField(blank=True, max_length=2000)
    status = models.CharField(max_length=32, choices=job_status_pairs,
                              default="received")
    url = models.URLField(blank=True, max_length=2000)


class PipelineJob(ParsingJob):

    cfr_title = models.IntegerField()
    cfr_part = models.IntegerField()
    only_latest = models.BooleanField(default=False)


class ProposalPipelineJob(ParsingJob):

    file_hexhash = models.CharField(max_length=64)
    only_latest = models.BooleanField(default=True)


class RegulationFile(models.Model):

    contents = models.BinaryField()
    file = models.FileField(null=True)  # noqa
    filename = models.CharField(default=None, max_length=512, null=True)
    hexhash = models.CharField(max_length=64, primary_key=True)
    url = models.URLField(blank=True, max_length=2000)
