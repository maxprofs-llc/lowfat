# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-23 09:39
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lowfat', '0149_add_fund_approval_chain'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='termsandconditions',
            options={'ordering': ['-year'], 'verbose_name_plural': 'terms and conditions'},
        ),
        migrations.AlterField(
            model_name='claimant',
            name='application_year',
            field=models.IntegerField(default=2020),
        ),
        migrations.AlterField(
            model_name='claimant',
            name='inauguration_grant_expiration',
            field=models.DateField(default=datetime.date(2022, 3, 31)),
        ),
        migrations.AlterField(
            model_name='historicalclaimant',
            name='application_year',
            field=models.IntegerField(default=2020),
        ),
        migrations.AlterField(
            model_name='historicalclaimant',
            name='inauguration_grant_expiration',
            field=models.DateField(default=datetime.date(2022, 3, 31)),
        ),
    ]
