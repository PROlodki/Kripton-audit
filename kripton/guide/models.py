from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.
User  = get_user_model()

class DepartmentManager(models.Manager):

    def create_department(self, name, description, head_of_department: User | None=None, parent=None, is_active=None):

        if name is None:
            raise TypeError('Department must have a name')
        if head_of_department is None:
            raise TypeError('Department must have a head')

        department = self.model(
            name=name,
            parent=parent,
            head_of_department=head_of_department,
            is_active=is_active,
            description=description
        )
        department.save()
        return department

class Department(models.Model):
    """Единая модель подразделения: справочник (guide) и отчёты (Reports)."""
    name = models.CharField(max_length=255, verbose_name='Название')
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Код'
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child',
        verbose_name='Родительское подразделение'
    )

    head_of_department = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        verbose_name='Руководитель'
    )

    description = models.CharField(
        max_length=255,
        verbose_name='Описание',
        blank=True
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name