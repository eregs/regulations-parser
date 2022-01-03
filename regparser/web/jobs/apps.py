from __future__ import unicode_literals

from django.apps import AppConfig


class JobsConfig(AppConfig):
    # Satisfies Django 3.2's  full python path to the application
    name = 'regparser.web.jobs'
