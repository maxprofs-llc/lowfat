# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-31 07:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fat', '0079_auto_20160819_1413'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fund',
            name='category',
            field=models.CharField(choices=[('A', 'Attending a conference/workshop'), ('H', 'Organising a conference/workshop (e.g. Software Carpentry)'), ('P', 'Policy related event'), ('O', 'Other')], default='O', max_length=1),
        ),
    ]
