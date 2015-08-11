# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transformation', '0002_auto_20150728_1038'),
    ]

    operations = [
        migrations.AddField(
            model_name='mapping',
            name='csvName',
            field=models.CharField(max_length='512', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='mapping',
            name='date',
            field=models.DateTimeField(auto_now_add=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='mapping',
            name='fileName',
            field=models.CharField(max_length='512', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='mapping',
            name='mappingFile',
            field=models.FileField(upload_to='transformation/mappings'),
        ),
    ]
