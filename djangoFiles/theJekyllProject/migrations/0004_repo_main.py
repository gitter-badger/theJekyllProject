# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-15 18:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('theJekyllProject', '0003_auto_20171010_1707'),
    ]

    operations = [
        migrations.AddField(
            model_name='repo',
            name='main',
            field=models.BooleanField(default=False),
        ),
    ]