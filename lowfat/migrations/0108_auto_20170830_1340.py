# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-30 13:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lowfat', '0107_auto_20170825_0854'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='advance_booking',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalexpense',
            name='advance_booking',
            field=models.BooleanField(default=False),
        ),
    ]
