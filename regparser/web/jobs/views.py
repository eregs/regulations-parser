import abc
import hashlib

import six
from django.http import HttpResponse
from rest_framework import generics, mixins, status
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response

from regparser.web.jobs.models import (PipelineJob, ProposalPipelineJob,
                                       RegulationFile)
from regparser.web.jobs.serializers import (FileUploadSerializer,
                                            PipelineJobSerializer,
                                            ProposalPipelineJobSerializer)
from regparser.web.jobs.utils import (add_redis_data_to_job_data,
                                      create_status_url, delete_eregs_job,
                                      eregs_site_api_url, file_url,
                                      queue_eregs_job,
                                      queue_notification_email)

renderer_classes = (
    JSONRenderer,
    BrowsableAPIRenderer
)


class BaseViewList(six.with_metaclass(abc.ABCMeta)):
    """
    Intended to be subclassed by classes subclassing ``JobViewList``.
    Contains the POST-related methods that are relevant to subclasses of
    ``JobViewList`` but not to ``JobViewList``.

    Should be in the subclass list before ``JobViewList``.
    """
    @abc.abstractmethod
    def build_eregs_args(self, validated_data):
        """
        Each type of parser job has its own set of arguments.
        The ``create`` method calls this method to construct the argument
        string specific to that type of job.

        :arg dict validated_data: Incoming data from the POST that's already
        been validated by the serializer.

        :rtype: list[str]
        :returns: The components of the argument string in list form.
        """
        raise NotImplementedError()

    def create(self, request, *args, **kwargs):
        """
        Overrides the ``create`` method of ``mixins.CreateModelMixin`` in order
        to add the new job to the Redis queue.

        Side effects
            Via ``queue_eregs_job`` and ``PipelineJobSerializer.save``, alters
            the redis queue and the DB.

        :arg HttpRequest request: the incoming request.

        :rtype: Response
        :returns: JSON or HTML of the information about the job (status 201),
            or about why the job couldn't be added (status 400).
        """
        serialized = self.get_serializer(data=request.data)
        serialized.is_valid(raise_exception=True)

        eregs_args = self.build_eregs_args(serialized.validated_data)
        job = queue_eregs_job(eregs_args, timeout=60 * 30, result_ttl=-1)

        # Paranoia--validate the values we provide:
        job_id = job.id
        for validator in serialized.get_fields()["job_id"].validators:
            validator(job_id)
        statusurl = create_status_url(job_id, sub_path=self.sub_path)
        for validator in serialized.get_fields()["url"].validators:
            validator(statusurl)

        if serialized.validated_data.get("notification_email"):
            queue_notification_email(
                job, statusurl,
                serialized.validated_data["notification_email"])
        serialized.save(job_id=job_id, url=statusurl,
                        destination=eregs_site_api_url)
        headers = self.get_success_headers(serialized.data)
        # Adding the Refresh header here so that the browser does the
        # user-friendly thing of redirecting the user to the page for the
        # newly-created object, even though use of the Refresh header is
        # frowned upon in some circles.
        #
        # Not using redirect via 302 or 303 so that non-browser users get the
        # 201 status code they expect upon a successful POST.
        #
        # I'm open to debate on this decision.
        headers["Refresh"] = "0;url={0}".format(statusurl)
        return Response(serialized.data, status=status.HTTP_201_CREATED,
                        headers=headers)


class JobViewList(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  generics.GenericAPIView):
    """
    Handles the list view for jobs of all types.
    Should be subclassed along with ``BaseViewList`` for classes handling
    specific job types.
    """
    queryset = PipelineJob.objects.all()
    renderer_classes = renderer_classes
    serializer_class = PipelineJobSerializer

    def filter_queryset(self, request, *args, **kwargs):
        """
        Overridden in order to get data from the Redis queue as well as the DB.

        Impure
            Pulls information from the DB and the Redis queue.

        :arg HttpRequest request: the incoming request.

        :rtype: list[PipelineJob]
        :returns: List of PipelineJob objects.
        """
        queryset = super(JobViewList, self).filter_queryset(request, *args,
                                                            **kwargs)
        queryset = add_redis_data_to_job_data(queryset)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class JobViewInstance(mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin,
                      generics.GenericAPIView):
    queryset = PipelineJob.objects.all()
    renderer_classes = renderer_classes
    lookup_field = "job_id"
    serializer_class = PipelineJobSerializer

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Overridden in order to remove the job from the Redis queue as well as
        the DB.

        Side Effects
            Via ``delete_eregs_job``, alters the Redis queue and the DB.

        :arg HttpRequest request: the incoming request.

        :rtype: Response
        :returns: JSON or HTML of the information about the job.
        """
        instance = self.get_object()
        job_id = instance.job_id
        self.perform_destroy(instance)
        delete_eregs_job(job_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

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


class PipelineJobViewList(BaseViewList, JobViewList):
    queryset = PipelineJob.objects.all()
    serializer_class = PipelineJobSerializer
    sub_path = "regulations/"

    def build_eregs_args(self, validated_data):
        """
        Overrides the method from ``BaseViewList`` in order to pass the
        arguments appropriate for the ``pipeline`` command.

        It returns a list of string components that can be passed to the
        `eregs` task runner. For example::

            ["pipeline", "0", "0", "http://some.url/"]

        :arg dict validated_data: Incoming data from the POST that's already
        been validated by the serializer.

        :rtype: list[str]
        :returns: The components of the argument string in list form.
        """
        return [
            "pipeline",
            str(validated_data["cfr_title"]),
            str(validated_data["cfr_part"]),
            eregs_site_api_url,
        ]

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class PipelineJobViewInstance(JobViewInstance):
    queryset = PipelineJob.objects.all()
    serializer_class = PipelineJobSerializer
    sub_path = "regulations/"


class ProposalPipelineJobViewList(BaseViewList, JobViewList):
    queryset = ProposalPipelineJob.objects.all()
    serializer_class = ProposalPipelineJobSerializer
    sub_path = "notices/"

    def build_eregs_args(self, validated_data):
        """
        Overrides the method from ``BaseViewList`` in order to pass the
        arguments appropriate for the ``proposal_pipeline`` command.

        It returns a list of string components that can be passed to the
        `eregs` task runner. For example::

            ["proposal_pipeline", "/tmp/tmp.xml", "http://some.url/"]

        Impure
            Reads the contents of the proposal file from the filesystem (in
            future, likely some other file storage, but impure either way).

        :arg dict validated_data: Incoming data from the POST that's already
        been validated by the serializer.

        :rtype: list[str]
        :returns: The components of the argument string in list form.
        """
        reg_file = RegulationFile.objects.get(
            hexhash=validated_data["file_hexhash"])
        # TODO: This is a total hack; we should not be storing the contents in
        # the DB but reading the file from the filesystem. Only doing this
        # temporarily before changing the proposal_pipeline command to work
        # differently.
        path = reg_file.file.storage.path(reg_file.file.name)
        return [
            "proposal_pipeline",
            path,
            eregs_site_api_url
        ]

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ProposalPipelineJobViewInstance(JobViewInstance):
    queryset = ProposalPipelineJob.objects.all()
    serializer_class = ProposalPipelineJobSerializer
    sub_path = "notices/"


class FileUploadView(mixins.ListModelMixin, mixins.CreateModelMixin,
                     generics.GenericAPIView):
    parser_classes = (FileUploadParser, MultiPartParser)
    parser_classes = (MultiPartParser,)
    serializer_class = FileUploadSerializer
    queryset = RegulationFile.objects.all()
    lookup_field = "hexhash"
    size_limit = 100000000  # Arbitrary 100MB limit.

    def create(self, request, *args, **kwargs):
        """
        Overrides the ``create`` method of ``mixins.CreateModelMixin`` in order
        to add the file contents to the database.

        Side effects
            Alters the DB.

        :arg HttpRequest request: the incoming request.

        :rtype: Response
        :returns: JSON or HTML of the information about the file (status 201),
            or about why the file couldn't be added (status 400).
        """
        serialized = self.get_serializer(data=request.data)
        serialized.is_valid(raise_exception=True)

        uploaded_file = request.data["file"]
        if uploaded_file.size > self.size_limit:
            return Response(
                dict(error="File too large ({0}-byte limit).".format(
                    self.size_limit)),
                status=status.HTTP_400_BAD_REQUEST
            )
        if uploaded_file.multiple_chunks():
            contents = b"".join(chunk for chunk in uploaded_file.chunks())
        else:
            contents = uploaded_file.read()
        sha = hashlib.sha256(contents)
        hexhash = sha.hexdigest()
        filename = uploaded_file.name
        url = file_url(hexhash)

        if not RegulationFile.objects.filter(hexhash=hexhash).exists():
            serialized.save(contents=contents, file=uploaded_file,
                            filename=filename, hexhash=hexhash, url=url)
            headers = self.get_success_headers(serialized.data)
            return Response(serialized.data, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            return Response(dict(error="File already present."),
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class FileUploadViewInstance(mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                             generics.GenericAPIView):
    serializer_class = FileUploadSerializer
    queryset = RegulationFile.objects.all()
    lookup_field = "hexhash"

    def get(self, request, *args, **kwargs):
        """
        Overrides the method from ``RetrieveModelMixin`` so that we return the
        contents of the file instead of a JSON object representing the file.

        Impure
            Reads from the DB.

        :arg HttpRequest request: the incoming request.

        :rtype: Response
        :returns: The raw contents of the file.
        """
        # Is the next line the best way to kick off a 404 if there's no match?
        self.retrieve(request, *args, **kwargs)

        uploaded_file = RegulationFile.objects.get(hexhash=kwargs["hexhash"])
        return HttpResponse(uploaded_file.contents)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
