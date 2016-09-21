# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0009_auto_20160824_2347'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelinejob',
            name='status',
            field=models.CharField(default=b'received', max_length=32, choices=[(b'complete', b'complete'), (b'complete_with_errors', b'complete_with_errors'), (b'failed', b'failed'), (b'in_progress', b'in_progress'), (b'received', b'received')]),
        ),
        migrations.AlterField(
            model_name='proposalpipelinejob',
            name='status',
            field=models.CharField(default=b'received', max_length=32, choices=[(b'complete', b'complete'), (b'complete_with_errors', b'complete_with_errors'), (b'failed', b'failed'), (b'in_progress', b'in_progress'), (b'received', b'received')]),
        ),
    ]
