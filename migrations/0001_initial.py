# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalTriple',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rdf_subject', models.CharField(max_length=b'512')),
                ('rdf_object', models.CharField(max_length=b'512')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Column',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('topic', models.CharField(max_length=b'512')),
                ('rdf_predicate', models.CharField(max_length=b'512')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CSV',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rdf_subject', models.CharField(max_length=b'512')),
                ('additional_triples', models.ForeignKey(verbose_name=b'additional triples', to='transformation.AdditionalTriple')),
                ('colums', models.ForeignKey(verbose_name=b'one column of the CSV', to='transformation.Column')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.CharField(max_length=b'512')),
                ('index', models.IntegerField()),
                ('rdf_object', models.CharField(max_length=b'512')),
                ('data_type', models.IntegerField(default=0, choices=[(0, b'none'), (1, b'reconciliated'), (2, b'Integer'), (3, b'Date'), (4, b'Text'), (4, b'Currency')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Interest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=b'512')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=b'512')),
                ('last_name', models.CharField(max_length=b'512')),
                ('interest', models.ForeignKey(verbose_name=b"user's field of interest", to='transformation.Interest')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='csv',
            name='owner',
            field=models.ForeignKey(verbose_name=b'Owner / creator of represented data model', to='transformation.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='column',
            name='fields',
            field=models.ForeignKey(verbose_name=b'single db fields', to='transformation.Field'),
            preserve_default=True,
        ),
    ]
