# Generated migration for DataSource load status fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasources', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasource',
            name='last_load_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('idle', 'Не загружалось'),
                    ('loading', 'Загрузка'),
                    ('success', 'Успешно'),
                    ('error', 'Ошибка'),
                ],
                default='idle',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='datasource',
            name='last_load_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='datasource',
            name='last_load_error',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='datasource',
            name='last_load_rows',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='connection_data',
            field=models.JSONField(default=dict),
        ),
    ]
