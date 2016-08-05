# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-08-04 14:53
from __future__ import unicode_literals

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('fat', '0053_auto_20160804_1447'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='country',
            field=django_countries.fields.CountryField(default='GB', max_length=2),
        ),
        migrations.AlterField(
            model_name='fellow',
            name='home_country',
            field=django_countries.fields.CountryField(default='GB', max_length=2),
        ),
    ]