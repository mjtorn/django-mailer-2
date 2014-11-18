# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def populate_subject_body(apps, schema_editor):
    """
    """

    Message = apps.get_model('mailer', 'Message')

    q = models.Q(subject__isnull=True) | models.Q(body__isnull=True)
    msgs = Message.objects.filter(q)

    # Resetting the pickled EmailObject resets subject and body
    for msg in msgs:
        msg.email = msg.email
        msg.save()


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0002_auto_20141118_0316'),
    ]

    operations = [
        migrations.RunPython(populate_subject_body)
    ]
