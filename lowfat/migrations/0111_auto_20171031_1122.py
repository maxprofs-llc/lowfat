# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-31 11:22
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lowfat', '0110_auto_20171003_1358'),
    ]

    operations = [
        migrations.RenameField(
            model_name='claimant',
            old_name='software_carpentry_instructor',
            new_name='carpentries_instructor',
        ),
        migrations.RenameField(
            model_name='historicalclaimant',
            old_name='software_carpentry_instructor',
            new_name='carpentries_instructor',
        ),
        migrations.RemoveField(
            model_name='claimant',
            name='data_carpentry_instructor',
        ),
        migrations.RemoveField(
            model_name='historicalclaimant',
            name='data_carpentry_instructor',
        ),
    ]