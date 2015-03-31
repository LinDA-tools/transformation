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
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
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
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('topic', models.CharField(max_length='512')),
                ('rdf_predicate', models.CharField(max_length='512')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CSV',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('rdf_subject', models.CharField(max_length='512')),
                ('additional_triples', models.ForeignKey(verbose_name='additional triples', to='transformation.AdditionalTriple')),
                ('colums', models.ForeignKey(verbose_name='one column of the CSV', to='transformation.Column')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('content', models.CharField(max_length='512')),
                ('index', models.IntegerField()),
                ('rdf_object', models.CharField(max_length='512')),
                ('data_type', models.IntegerField(choices=[(0, 'none'), (1, 'reconciliated'), (2, 'Integer'), (3, 'Date'), (4, 'Text'), (4, 'Currency')], default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Interest',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length='512')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('first_name', models.CharField(max_length='512')),
                ('last_name', models.CharField(max_length='512')),
                ('interest', models.ForeignKey(verbose_name="user's field of interest", to='transformation.Interest')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='csv',
            name='owner',
            field=models.ForeignKey(verbose_name='Owner / creator of represented data model', to='transformation.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='column',
            name='fields',
            field=models.ForeignKey(verbose_name='single db fields', to='transformation.Field'),
            preserve_default=True,
        ),
    ]
