from django.db import models
from django.conf import settings


class DataSource(models.Model):
    TYPE_CHOICES = [
        ('csv', 'CSV file'),
        ('gsheet', 'Google Sheets'),
        ('postgres', 'PostgreSQL'),
    ]
    LOAD_STATUS_CHOICES = [
        ('idle', 'Не загружалось'),
        ('loading', 'Загрузка'),
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    connection_data = models.JSONField(default=dict)  # путь к файлу, URL или параметры подключения
    created_at = models.DateTimeField(auto_now_add=True)

    # Статус последней загрузки для API
    last_load_status = models.CharField(
        max_length=20, choices=LOAD_STATUS_CHOICES, default='idle', blank=True
    )
    last_load_at = models.DateTimeField(null=True, blank=True)
    last_load_error = models.TextField(blank=True)
    last_load_rows = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


