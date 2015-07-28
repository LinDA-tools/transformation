# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalTriple',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('rdf_subject', models.CharField(max_length='512')),
                ('rdf_object', models.CharField(max_length='512')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Column',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('topic', models.CharField(max_length='512')),
                ('rdf_predicate', models.CharField(max_length='512', blank=True, default=None, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CSV',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('rdf_subject', models.CharField(max_length='512', blank=True, default=None, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CSVFile',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('_data', models.TextField(blank=True, db_column='data')),
                ('file_name', models.CharField(max_length='512', blank=True, default=None, null=True)),
                ('csv', models.ForeignKey(to='transformation.CSV', default=None, null=True, blank=True, verbose_name='CSV representation this raw csv data belongs to')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('content', models.CharField(max_length='512')),
                ('index', models.IntegerField()),
                ('rdf_object', models.CharField(max_length='512', blank=True, default=None, null=True)),
                ('data_type', models.IntegerField(default=0, choices=[(0, 'none'), (1, 'reconciliated'), (2, 'Integer'), (3, 'Date'), (4, 'Text'), (4, 'Currency')])),
                ('column', models.ForeignKey(to='transformation.Column', default=None, null=True, blank=True, verbose_name='table column this is a single field of')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SaveMapping',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('mappingFile', models.FileField(upload_to='mappings')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='column',
            name='csv',
            field=models.ForeignKey(to='transformation.CSV', default=None, null=True, blank=True, verbose_name='CSV representation this column belongs to'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='additionaltriple',
            name='csv',
            field=models.ForeignKey(to='transformation.CSV', default=None, null=True, blank=True, verbose_name='CSV representation this additinal triple belongs to'),
            preserve_default=True,
        ),
    ]
