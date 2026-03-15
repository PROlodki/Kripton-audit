# Generated migration for ReportRequest.assigned_to

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Reports', '0005_report_submitted_approved'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='reportrequest',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_report_requests',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Назначено',
            ),
        ),
    ]
