# Generated migration: allow blank description on ReportRequest

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Reports', '0006_reportrequest_assigned_to'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportrequest',
            name='description',
            field=models.TextField(blank=True, default='', verbose_name='Описание'),
        ),
    ]
