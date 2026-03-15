# Generated migration for RealtimeEvent and UserActivity

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kripton', '0001_audit_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='RealtimeEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(db_index=True, max_length=50)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('read', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='realtime_events', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_seen', models.DateTimeField(auto_now=True, db_index=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='activity', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Активность пользователя',
                'verbose_name_plural': 'Активность пользователей',
            },
        ),
        migrations.AddIndex(
            model_name='realtimeevent',
            index=models.Index(fields=['user', 'read', 'created_at'], name='kripton_rea_user_id_5b0b0d_idx'),
        ),
    ]
