# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-02 16:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fellowms', '0019_auto_20160601_1512'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='status',
            field=models.CharField(choices=[('W', 'Not submitted yet'), ('S', 'Submitted (but not processed yet)'), ('P', 'Processing'), ('A', 'Approved (waiting reply from finances)'), ('F', 'Finished')], default='P', max_length=1),
        ),
    ]