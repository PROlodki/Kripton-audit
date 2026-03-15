from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import json

from kripton.guide.models import Department

User = settings.AUTH_USER_MODEL


class ReportType(models.Model):
    """Тип отчета"""
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Код'
    )
    description = models.TextField(verbose_name='Описание')
    template = models.TextField(
        blank=True,
        help_text='Шаблон отчета'
    )
    
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
    title = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.CASCADE,
        verbose_name='Тип отчета'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
        )
    
    # Ссылка на данные в ClickHouse (если используется)
    clickhouse_table = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Таблица ClickHouse'
    )
    clickhouse_query = models.TextField(
        blank=True,
        verbose_name='Запрос ClickHouse'
    )
    
    # Локальное хранение
    data = models.JSONField(default=dict, blank=True, verbose_name='Данные отчета')
    file = models.FileField(upload_to='reports/%Y/%m/%d/', null=True, blank=True, verbose_name='Файл')
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Создатель'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отправки')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reports',
        verbose_name='Утвердил'
    )
    
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
    )  # guide.Department — единая модель подразделений
    
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name='Тип отчета'
    )
    
    title = models.CharField(max_length=255, verbose_name='Название отчета')
    description = models.TextField(verbose_name='Описание', blank=True, default='')
    
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

    # Кто именно должен выполнить отчёт (подразделение знаем по department)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_report_requests',
        verbose_name='Назначено',
    )
    
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
        if self.department and self.department.head_of_department == user:
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

    def reject(self, user, rejection_reason=None):
        """Отклонить запрос (обёртка над approve с причиной)."""
        self.approve(user, rejection_reason=rejection_reason or '')
    
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
        if self.department and self.department.head_of_department == user:
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

class PersonalData(models.Model):
    
    user = models.ForeignKey(
        'authpage.User',  
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personal_data',
        verbose_name="Пользователь"
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel',
        verbose_name="Отдел"
    )
    
    last_name = models.CharField(
        max_length=100,
        verbose_name="Фамилия"
    )
    
    first_name = models.CharField(
        max_length=100,
        verbose_name="Имя"
    )
    
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Отчество"
    )
    
    position = models.CharField(
        max_length=255,
        verbose_name="Должность"
    )
    
    rank = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Звание"
    )
    
    hire_date = models.DateField(
        verbose_name="Дата приема на работу"
    )
    
    dismissal_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата увольнения"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )
    
    additional_data = models.TextField(
        blank=True,
        verbose_name="Дополнительные данные",
        help_text="Дополнительная информация"
    )
    
    # ========== МЕТАДАННЫЕ ==========
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    
    class Meta:
        """Мета-класс с настройками модели"""
        verbose_name = "Персональные данные"
        verbose_name_plural = "Персональные данные"
        ordering = ['last_name', 'first_name', 'middle_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['hire_date']),
            models.Index(fields=['position']),
        ]
    
    def __str__(self):
        return self.get_full_name()
    
    def get_full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)
    
    @property
    def work_experience(self):
        from datetime import date
        
        if not self.hire_date:
            return 0
        
        end_date = self.dismissal_date or date.today()
        
        years = end_date.year - self.hire_date.year
        
        if (end_date.month, end_date.day) < (self.hire_date.month, self.hire_date.day):
            years -= 1
        
        return max(0, years)
    
    @property
    def is_currently_employed(self):
        return self.is_active and not self.dismissal_date
    
    def save(self, *args, **kwargs):
        if self.dismissal_date and self.is_active:
            self.is_active = False
        
        if not self.dismissal_date and not self.is_active:
            self.is_active = True
        
        if self.hire_date and self.dismissal_date:
            if self.dismissal_date < self.hire_date:
                raise ValueError("Дата увольнения не может быть раньше даты приема")
        
        super().save(*args, **kwargs)
    
    def get_additional_data_dict(self):
        import json
        if self.additional_data:
            try:
                return json.loads(self.additional_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_additional_data(self, data_dict):
        import json
        self.additional_data = json.dumps(data_dict, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.get_full_name(),
            'last_name': self.last_name,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'position': self.position,
            'rank': self.rank,
            'department': str(self.department) if self.department else None,
            'department_id': self.department_id,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'dismissal_date': self.dismissal_date.isoformat() if self.dismissal_date else None,
            'is_active': self.is_active,
            'work_experience': self.work_experience,
            'is_currently_employed': self.is_currently_employed,
            'user_id': self.user_id,
            'additional_data': self.get_additional_data_dict(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
