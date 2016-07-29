from regparser.web.jobs.models import ParsingJob
from rest_framework import serializers


class ParsingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParsingJob
        fields = (
            "cfr_title",
            "cfr_part",
            "clear_cache",
            "destination",  # Unsure about whether this should accept user
                            # input or be set by the system.
            "job_id",
            "notification_email",
            "only_latest",
            "use_uploaded_metadata",
            "use_uploaded_regulation",
            "parser_errors",
            "regulation_url",
            "status",
            "url"
        )

    # Fields we don't want user input for are listed below.
    # For now, don't take user input for destination URL:
    destination = serializers.URLField(read_only=True)
    job_id = serializers.UUIDField(read_only=True)
    parser_errors = serializers.CharField(read_only=True)
    regulation_url = serializers.URLField(read_only=True)
    status = serializers.CharField(read_only=True)
    url = serializers.URLField(read_only=True)

    def save(self, **kwargs):
        super(ParsingJobSerializer, self).save(**kwargs)
