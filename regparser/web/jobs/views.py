from regparser.web.jobs.models import ParsingJob
from regparser.web.jobs.serializers import ParsingJobSerializer
from regparser.web.jobs.utils import (
    add_redis_data_to_job_data,
    queue_eregs_job,
    status_url
)
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework import generics
from rest_framework import mixins
from rest_framework import status

renderer_classes = (
    JSONRenderer,
    BrowsableAPIRenderer
)


class JobViewList(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  generics.GenericAPIView):
    queryset = ParsingJob.objects.all()
    renderer_classes = renderer_classes
    serializer_class = ParsingJobSerializer

    def filter_queryset(self, request, *args, **kwargs):
        """
        Overridden in order to get data from the Redis queue as well as the DB.

        Impure
            Pulls information from the DB and the Redis queue.

        :arg HttpRequest request: the incoming request.

        :rtype: list[ParsingJob]
        :returns: List of ParsingJob objects.
        """
        queryset = super(JobViewList, self).filter_queryset(request, *args,
                                                            **kwargs)
        queryset = add_redis_data_to_job_data(queryset)
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Overridden in order to add the new job to the Redis queue.

        Side effects
            Via ``queue_eregs_job`` and ``ParsingJobSerializer.save``, alters
            the redis queue and the DB.

        :arg HttpRequest request: the incoming request.

        :rtype: Response
        :returns: JSON or HTML of the information about the job (status 201),
            or about why the job couldn't be added (status 400).
        """
        serialized = self.get_serializer(data=request.data)
        serialized.is_valid(raise_exception=True)
        eregs_args = [
            "pipeline",
            str(serialized.validated_data["cfr_title"]),
            str(serialized.validated_data["cfr_part"]),
            "./testing"
        ]
        job = queue_eregs_job(eregs_args, timeout=60*30, result_ttl=-1)

        # Paranoia--validate the values we provide:
        job_id = job.id
        for validator in serialized.get_fields()["job_id"].validators:
            validator(job_id)
        statusurl = status_url(job_id)
        for validator in serialized.get_fields()["url"].validators:
            validator(statusurl)

        serialized.save(job_id=job_id, url=status_url(job_id))
        headers = self.get_success_headers(serialized.data)
        """
        Adding the Refresh header here so that the browser does the
        user-friendly thing of redirecting the user to the page for the
        newly-created object, even though use of the Refresh header is
        frowned upon in some circles.

        Not using redirect via 302 or 303 so that non-browser users get the
        201 status code they expect upon a successful POST.

        I'm open to debate on this decision.
        """
        headers["Refresh"] = "0;url=%s" % statusurl
        return Response(serialized.data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class JobViewInstance(mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin,
                      generics.GenericAPIView):
    queryset = ParsingJob.objects.all()
    renderer_classes = renderer_classes
    serializer_class = ParsingJobSerializer
    lookup_field = "job_id"

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Overridden in order to get data from the Redis queue as well as the DB.

        Impure
            Pulls information from the DB and the Redis queue.

        :arg HttpRequest request: the incoming request.

        :rtype: Response
        :returns: JSON or HTML of the information about the job.
        """
        instance = self.get_object()
        instance = add_redis_data_to_job_data([instance])[0]
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
