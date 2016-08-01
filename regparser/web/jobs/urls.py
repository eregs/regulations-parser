from django.conf.urls import url
from regparser.web.jobs import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^job/$', views.JobViewList.as_view()),
    url(r'^job/(?P<job_id>[-a-z0-9]+)/$',
        views.JobViewInstance.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)
