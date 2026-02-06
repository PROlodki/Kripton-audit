from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Лог аудита: кто, что сделал, над каким ресурсом, когда и откуда."""

    class ActionType(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Обновление'
        DELETE = 'delete', 'Удаление'
        VIEW = 'view', 'Просмотр'
        LOGIN = 'login', 'Вход'
        LOGOUT = 'logout', 'Выход'
        APPROVE = 'approve', 'Утверждение'
        REJECT = 'reject', 'Отклонение'
        OTHER = 'other', 'Другое'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Пользователь',
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
        verbose_name='Тип действия',
    )
    resource_type = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name='Тип ресурса',
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name='ID ресурса',
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Детали',
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP-адрес',
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='User-Agent',
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Время',
    )

    class Meta:
        verbose_name = 'Запись лога аудита'
        verbose_name_plural = 'Лог аудита'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp'], name='audit_user_ts_idx'),
            models.Index(fields=['resource_type', 'resource_id'], name='audit_resource_idx'),
            models.Index(fields=['action_type', 'timestamp'], name='audit_action_ts_idx'),
            models.Index(fields=['timestamp'], name='audit_timestamp_idx'),
        ]

    def __str__(self):
        user_str = str(self.user) if self.user else '—'
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {user_str} | {self.get_action_type_display()} | {self.resource_type or '—'}"
