"""
AuditService — логирование действий: log_action, автоматическое CRUD, доступ к данным, экспорт логов.
"""
from kripton.audit import log_audit


class AuditService:
    """Единая точка логирования для отчётов и дашбордов."""

    @staticmethod
    def log_action(
        request=None,
        action_type: str = 'other',
        resource_type: str = '',
        resource_id: str = '',
        details: dict = None,
        user=None,
        department_id=None,
        department_name: str = '',
        department_code: str = '',
    ):
        """
        Логирование действия пользователя (Django + ClickHouse).
        action_type: create, update, delete, view, login, logout, approve, reject, other.
        """
        return log_audit(
            request=request,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            user=user,
            department_id=department_id,
            department_name=department_name,
            department_code=department_code,
        )

    @staticmethod
    def log_crud(instance, action: str, request=None, user=None):
        """
        Автоматическое логирование CRUD по модели.
        action: 'create' | 'update' | 'delete'
        """
        model_name = instance.__class__.__name__
        pk = getattr(instance, 'pk', None) or getattr(instance, 'id', None)
        resource_type = model_name.lower()
        resource_id = str(pk) if pk is not None else ''
        details = {}
        if action == 'create' and hasattr(instance, 'title'):
            details['title'] = getattr(instance, 'title', '')[:200]
        if action in ('update', 'delete') and hasattr(instance, 'title'):
            details['title'] = getattr(instance, 'title', '')[:200]
        dept_id, dept_name, dept_code = None, '', ''
        if hasattr(instance, 'department') and instance.department:
            d = instance.department
            dept_id, dept_name = d.id, d.name or ''
            dept_code = getattr(d, 'code', '') or ''
        return AuditService.log_action(
            request=request,
            action_type=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            user=user or (getattr(request, 'user', None) if request else None),
            department_id=dept_id,
            department_name=dept_name,
            department_code=dept_code,
        )

    @staticmethod
    def log_data_access(request, resource_type: str, resource_id: str = '', details: dict = None):
        """Логирование доступа к данным (просмотр отчёта, выгрузка, предпросмотр)."""
        return AuditService.log_action(
            request=request,
            action_type='view',
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )


# Экспорт логов реализован в kripton.audit_views.AuditLogViewSet.export (CSV).
