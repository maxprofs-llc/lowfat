# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-25 11:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lowfat', '0084_auto_20170112_1614'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='funds_from',
            field=models.CharField(choices=[('C', 'Continuing (claimantship)'), ('I', 'Core (Software Sustainability Institute)'), ('F', 'Grant (inauguration claimantship)')], default='G', max_length=1),
        ),
    ]
