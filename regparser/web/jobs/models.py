from django.db import models


class ParsingJob(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    cfr_title = models.IntegerField()
    cfr_part = models.IntegerField()
    clear_cache = models.BooleanField(default=False)
    destination = models.URLField(default="http://fake-reg-site.gov/api",
                                  max_length=2000)
    notification_email = models.EmailField(blank="True", max_length=254)
    only_latest = models.BooleanField(default=False)
    job_id = models.UUIDField(default=None, null=True)
    use_uploaded_metadata = models.UUIDField(default=None, null=True)
    use_uploaded_regulation = models.UUIDField(default=None, null=True)

    parser_errors = models.TextField(blank=True)
    regulation_url = models.URLField(blank=True, max_length=2000)
    status = models.CharField(max_length=32, choices=(
        ("received", "received"),
        ("in_progress", "in_progress"),
        ("failed", "failed"),
        ("complete", "complete"),
        ("complete_with_errors", "complete_with_errors")
    ), default="received")
    url = models.URLField(blank=True, max_length=2000)
