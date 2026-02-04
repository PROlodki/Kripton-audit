from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

# Используем вашу кастомную модель пользователя
User = settings.AUTH_USER_MODEL


class Department(models.Model):
    """Подразделение"""
    name = models.CharField(max_length=200, verbose_name='Название')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код')
    description = models.TextField(blank=True, verbose_name='Описание')
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        verbose_name='Руководитель'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class ReportType(models.Model):
    """Тип отчета"""
    name = models.CharField(max_length=200, verbose_name='Название')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код')
    description = models.TextField(verbose_name='Описание')
    template = models.TextField(blank=True, help_text='Шаблон отчета')
    
    # Кто может просматривать отчеты этого типа
    stakeholders = models.ManyToManyField(
        User,
        blank=True,
        related_name='stakeholder_report_types',
        verbose_name='Заинтересованные лица'
    )
    
    # Кто может создавать запросы этого типа
    allowed_creators = models.ManyToManyField(
        User,
        blank=True,
        related_name='creatable_report_types',
        verbose_name='Кто может создавать'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Тип отчета'
        verbose_name_plural = 'Типы отчетов'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Report(models.Model):
    """Созданный отчет"""
    title = models.CharField(max_length=255, verbose_name='Название')
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE, verbose_name='Тип отчета')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    # Ссылка на данные в ClickHouse (если используется)
    clickhouse_table = models.CharField(max_length=200, blank=True, verbose_name='Таблица ClickHouse')
    clickhouse_query = models.TextField(blank=True, verbose_name='Запрос ClickHouse')
    
    # Локальное хранение
    data = models.JSONField(default=dict, blank=True, verbose_name='Данные отчета')
    file = models.FileField(upload_to='reports/%Y/%m/%d/', null=True, blank=True, verbose_name='Файл')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class ReportRequest(models.Model):
    """Запрос на создание отчета"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает утверждения'
        APPROVED = 'approved', 'Утвержден'
        REJECTED = 'rejected', 'Отклонен'
        IN_PROGRESS = 'in_progress', 'В работе'
        COMPLETED = 'completed', 'Завершен'
    
    # Основные поля
    requester = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='report_requests',
        verbose_name='Заявитель'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='report_requests',
        verbose_name='Подразделение'
    )
    
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name='Тип отчета'
    )
    
    title = models.CharField(max_length=255, verbose_name='Название отчета')
    description = models.TextField(verbose_name='Описание')
    
    # Статус
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    
    # Связь с созданным отчетом
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_request',
        verbose_name='Созданный отчет'
    )
    
    # Утверждение
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests',
        verbose_name='Утвердил'
    )
    
    rejection_reason = models.TextField(blank=True, verbose_name='Причина отклонения')
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    
    # Дополнительные поля
    priority = models.IntegerField(
        default=3,
        choices=[(1, 'Высокий'), (2, 'Средний'), (3, 'Низкий')],
        verbose_name='Приоритет'
    )
    
    deadline = models.DateField(null=True, blank=True, verbose_name='Срок выполнения')
    
    class Meta:
        verbose_name = 'Запрос отчета'
        verbose_name_plural = 'Запросы отчетов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Запрос #{self.id}: {self.title} ({self.get_status_display()})"
    
    def clean(self):
        """Валидация данных"""
        errors = {}
        
        # Проверка: отчет может быть привязан только к утвержденным запросам
        if self.report and self.status not in [self.Status.APPROVED, self.Status.COMPLETED]:
            errors['report'] = 'Отчет может быть привязан только к утвержденным запросам'
        
        # Проверка: причина отклонения обязательна для отклоненных запросов
        if self.status == self.Status.REJECTED and not self.rejection_reason:
            errors['rejection_reason'] = 'Укажите причину отклонения'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Переопределение сохранения с валидацией"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def can_approve(self, user):
        """
        Проверка прав пользователя на утверждение/отклонение
        """
        if not user.is_authenticated:
            return False
        
        # Администраторы могут утверждать любые запросы
        if user.is_superuser or user.is_staff:
            return True
        
        # Проверка по группам
        from django.contrib.auth.models import Group
        is_admin = user.groups.filter(name='Администраторы').exists()
        is_manager = user.groups.filter(name='Менеджеры').exists()
        
        if is_admin or is_manager:
            return True
        
        # Руководитель отдела может утверждать запросы своего отдела
        if hasattr(self.department, 'head') and self.department.head == user:
            return True
        
        # Нельзя утверждать свои собственные запросы
        if user == self.requester:
            return False
        
        # Можно работать только с запросами в статусе ожидания
        if self.status != self.Status.PENDING:
            return False
        
        return True
    
    def approve(self, user, rejection_reason=None):
        """Утвердить или отклонить запрос"""
        if not self.can_approve(user):
            raise PermissionError(f"Пользователь {user} не может утвердить этот запрос")
        
        if rejection_reason:
            self.status = self.Status.REJECTED
            self.rejection_reason = rejection_reason
        else:
            self.status = self.Status.APPROVED
            self.approved_at = timezone.now()
        
        self.approved_by = user
        self.save()
    
    def can_view(self, user):
        """
        Проверка прав на просмотр запроса
        """
        if not user.is_authenticated:
            return False
        
        # Администраторы и менеджеры видят все
        if user.is_superuser or user.is_staff:
            return True
        
        # Заявитель видит свои запросы
        if user == self.requester:
            return True
        
        # Руководитель отдела видит запросы своего отдела
        if hasattr(self.department, 'head') and self.department.head == user:
            return True
        
        # Заинтересованные лица видят запросы своих типов отчетов
        if user in self.report_type.stakeholders.all():
            return True
        
        # Проверка по группам
        from django.contrib.auth.models import Group
        is_manager = user.groups.filter(name='Менеджеры').exists()
        if is_manager:
            return True
        
        return False
