# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-12-26 11:00
from __future__ import unicode_literals

from django.db import migrations, models

from django_pg_bulk_update.compatibility import jsonb_available, hstore_available, array_available, \
    get_postgres_version, Postgres94MergeJSONBMigration

test_model_fields = [
    ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
    ('int_field', models.IntegerField(null=True, blank=True)),
    ('name', models.CharField(max_length=50, null=True, blank=True))
]

if jsonb_available():
    from django.contrib.postgres.fields import JSONField
    test_model_fields.append(('json_field', JSONField(null=True, blank=True)))

if array_available():
    from django.contrib.postgres.fields import ArrayField
    test_model_fields.append(('array_field', ArrayField(models.IntegerField(), null=True, blank=True)))

if hstore_available():
    from django.contrib.postgres.fields import HStoreField
    test_model_fields.append(('hstore_field', HStoreField(null=True, blank=True)))


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=test_model_fields,
            options={
                'abstract': False,
            }
        ),
        migrations.CreateModel(
            name='UniqueNotPrimary',
            fields=(
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('int_field', models.IntegerField(unique=True)),
            ),
            options={
                'abstract': False,
            }
        ),
        migrations.AlterUniqueTogether(name='TestModel', unique_together=[('id', 'name')])
    ]


if hstore_available():
    from django.contrib.postgres.operations import HStoreExtension
    Migration.operations = [HStoreExtension()] + Migration.operations

if jsonb_available() and get_postgres_version() < (9, 5):
    Migration.operations += [Postgres94MergeJSONBMigration()]
