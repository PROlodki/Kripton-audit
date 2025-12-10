from django.db import models
from django.conf import settings

class DataSource(models.Model):
    TYPE_CHOICES = [
        ('csv', 'CSV file'),
        ('gsheet', 'Google Sheets'),
        ('postgres', 'PostgreSQL'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    connection_data = models.JSONField()  # путь к файлу или URL
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name