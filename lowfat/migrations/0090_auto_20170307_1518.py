# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-07 15:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

def add_author_to_blog(apps, schema_editor):  # pylint: disable=unused-argument
    """Author is the claimant"""
    Blog = apps.get_model("lowfat", "Blog")  # pylint: disable=invalid-name
    for blog in Blog.objects.all():
        blog.author = blog.fund.claimant
        blog.save()

class Migration(migrations.Migration):

    dependencies = [
        ('lowfat', '0089_auto_20170306_1706'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lowfat.Claimant'),
        ),
        migrations.AddField(
            model_name='historicalblog',
            name='author',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='lowfat.Claimant'),
        ),
        migrations.AlterField(
            model_name='blog',
            name='fund',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lowfat.Fund'),
        ),
        migrations.RunPython(add_author_to_blog),
    ]
