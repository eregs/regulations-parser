# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ParsingJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('cfr_title', models.IntegerField()),
                ('cfr_part', models.IntegerField()),
                ('clear_cache', models.BooleanField(default=False)),
                ('destination', models.URLField(default=b'http://fake-reg-site.gov/api', max_length=2000)),
                ('notification_email', models.EmailField(max_length=254, blank=b'True')),
                ('only_latest', models.BooleanField(default=False)),
                ('job_id', models.UUIDField(default=None, null=True)),
                ('use_uploaded_metadata', models.UUIDField(default=None, null=True)),
                ('use_uploaded_regulation', models.UUIDField(default=None, null=True)),
                ('parser_errors', models.TextField(blank=True)),
                ('regulation_url', models.URLField(max_length=2000, blank=True)),
                ('status', models.CharField(default=b'received', max_length=32, choices=[(b'received', b'received'), (b'in_progress', b'in_progress'), (b'failed', b'failed'), (b'complete', b'complete'), (b'complete_with_errors', b'complete_with_errors')])),
                ('status_url', models.URLField(max_length=2000, blank=True)),
            ],
        ),
    ]
