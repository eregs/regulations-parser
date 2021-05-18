from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from regparser.web.jobs import views

urlpatterns = [
    url(r'^jobs(/)$', views.JobViewList.as_view()),
    url(r'^jobs/regulations(/)$', views.PipelineJobViewList.as_view()),
    url(r'^jobs/regulations(/)(?P<job_id>[-a-z0-9]+)(/)$',
        views.PipelineJobViewInstance.as_view()),
    url(r'^jobs/notices(/)$',
        views.ProposalPipelineJobViewList.as_view()),
    url(r'^jobs/notices(/)(?P<job_id>[-a-z0-9]+)(/)$',
        views.ProposalPipelineJobViewInstance.as_view()),
    url(r'^jobs/files/(?P<hexhash>[a-z0-9]{64})(/)$',
        views.FileUploadViewInstance.as_view()),
    url(r'^jobs/files(/)$',
        views.FileUploadView.as_view()),
    url(r'^jobs/(?P<job_id>[-a-z0-9]+)(/)$',
        views.JobViewInstance.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)
