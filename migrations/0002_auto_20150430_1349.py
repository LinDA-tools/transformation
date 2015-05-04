# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transformation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSVFile',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('_data', models.TextField(blank=True, db_column='data')),
                ('file_name', models.CharField(default=None, max_length='512', null=True, blank=True)),
                ('csv', models.ForeignKey(to='transformation.CSV', default=None, verbose_name='CSV representation this raw csv data belongs to', blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='person',
            name='interest',
        ),
        migrations.DeleteModel(
            name='Interest',
        ),
        migrations.RemoveField(
            model_name='column',
            name='fields',
        ),
        migrations.RemoveField(
            model_name='csv',
            name='additional_triples',
        ),
        migrations.RemoveField(
            model_name='csv',
            name='colums',
        ),
        migrations.RemoveField(
            model_name='csv',
            name='owner',
        ),
        migrations.DeleteModel(
            name='Person',
        ),
        migrations.AddField(
            model_name='additionaltriple',
            name='csv',
            field=models.ForeignKey(to='transformation.CSV', default=None, verbose_name='CSV representation this additinal triple belongs to', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='column',
            name='csv',
            field=models.ForeignKey(to='transformation.CSV', default=None, verbose_name='CSV representation this column belongs to', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='field',
            name='column',
            field=models.ForeignKey(to='transformation.Column', default=None, verbose_name='table column this is a single field of', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='column',
            name='rdf_predicate',
            field=models.CharField(default=None, max_length='512', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='csv',
            name='rdf_subject',
            field=models.CharField(default=None, max_length='512', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='field',
            name='rdf_object',
            field=models.CharField(default=None, max_length='512', null=True, blank=True),
        ),
    ]
