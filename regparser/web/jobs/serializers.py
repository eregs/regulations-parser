from rest_framework import serializers

from regparser.web.jobs.models import (ParsingJob, PipelineJob,
                                       ProposalPipelineJob, RegulationFile)


class ParsingJobSerializer(serializers.ModelSerializer):

    class Meta:
        model = ParsingJob
        fields = (
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


class PipelineJobSerializer(ParsingJobSerializer):

    class Meta(ParsingJobSerializer.Meta):
        model = PipelineJob
        fields = ParsingJobSerializer.Meta.fields + (
            "cfr_title",
            "cfr_part"
        )


class ProposalPipelineJobSerializer(ParsingJobSerializer):

    class Meta(ParsingJobSerializer.Meta):
        model = ProposalPipelineJob
        fields = ParsingJobSerializer.Meta.fields + (
            "file_hexhash",
        )

    # Fields we don't want user input for are listed below.
    file_hexhash = serializers.CharField(max_length=64)


class FileUploadSerializer(serializers.ModelSerializer):

    class Meta:
        model = RegulationFile
        fields = (
            "contents",
            "file",
            "filename",
            "hexhash",
            "url"
        )

    contents = serializers.SerializerMethodField()
    file = serializers.FileField()  # noqa
    filename = serializers.CharField(read_only=True)
    hexhash = serializers.CharField(read_only=True)
    url = serializers.URLField(read_only=True)

    @staticmethod
    def get_contents(obj):
        return "File contents not shown."
