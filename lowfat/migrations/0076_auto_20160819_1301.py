# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-19 13:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lowfat', '0075_auto_20160818_1415'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='recipient_fullname',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]