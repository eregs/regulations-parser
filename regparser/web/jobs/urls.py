from django.conf.urls import url
from regparser.web.jobs import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^job(/)$', views.JobViewList.as_view()),
    url(r'^job/pipeline(/)$', views.PipelineJobViewList.as_view()),
    url(r'^job/pipeline(/)(?P<job_id>[-a-z0-9]+)(/)$',
        views.PipelineJobViewInstance.as_view()),
    url(r'^job/proposal-pipeline(/)$',
        views.ProposalPipelineJobViewList.as_view()),
    url(r'^job/proposal-pipeline(/)(?P<job_id>[-a-z0-9]+)(/)$',
        views.ProposalPipelineJobViewInstance.as_view()),
    url(r'^job/upload/(?P<hexhash>[a-z0-9]{32})(/)$',
        views.FileUploadViewInstance.as_view()),
    url(r'^job/upload(/)$',
        views.FileUploadView.as_view()),
    url(r'^job/(?P<job_id>[-a-z0-9]+)(/)$',
        views.JobViewInstance.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)
