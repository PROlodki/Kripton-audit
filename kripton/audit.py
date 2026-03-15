"""
Вспомогательные функции для записи в лог аудита.
Использование: log_audit(request, 'create', resource_type='report', resource_id='42', details={...})
"""
from .models import AuditLog


def get_client_ip(request):
    """IP клиента с учётом X-Forwarded-For (прокси/балансировщики)."""
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_user_agent(request):
    """User-Agent из запроса."""
    if not request:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:500]


def log_audit(
    request=None,
    action_type='other',
    resource_type='',
    resource_id='',
    details=None,
    user=None,
    department_id=None,
    department_name='',
    department_code='',
):
    """
    Создать запись в логе аудита (Django + при наличии ClickHouse — дублирование в CH).

    :param request: HttpRequest (для user, ip_address, user_agent)
    :param action_type: строка из AuditLog.ActionType (create, update, delete, view, login, logout, approve, reject, other)
    :param resource_type: тип ресурса (например 'report', 'report_request', 'department')
    :param resource_id: идентификатор ресурса (строка или будет приведён к str)
    :param details: dict с дополнительными данными (сохраняется в JSON)
    :param user: пользователь (если не передан, берётся request.user)
    :param department_id: id подразделения для дашбордов (опционально)
    :param department_name: название подразделения (опционально)
    :param department_code: код подразделения (опционально)
    """
    if details is None:
        details = {}
    if request:
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        if user is None:
            user = getattr(request, 'user', None) if request else None
            if hasattr(user, 'is_authenticated') and not user.is_authenticated:
                user = None
    else:
        ip = None
        user_agent = ''

    log_entry = AuditLog.objects.create(
        user=user,
        action_type=action_type,
        resource_type=str(resource_type)[:100] if resource_type else '',
        resource_id=str(resource_id)[:100] if resource_id else '',
        details=details,
        ip_address=ip,
        user_agent=user_agent,
    )

    # Дублирование в ClickHouse для отчётов/дашбордов (при недоступности CH — тихо игнорируем)
    try:
        from kripton.clickhouse_services import push_audit_log
        from django.utils import timezone
        ts = log_entry.timestamp
        if ts.tzinfo:
            ts = timezone.make_naive(ts, timezone=timezone.utc)
        push_audit_log(
            timestamp=ts,
            user_id=log_entry.user_id,
            username=str(log_entry.user) if log_entry.user else '',
            action_type=log_entry.action_type,
            resource_type=log_entry.resource_type or '',
            resource_id=log_entry.resource_id or '',
            details=log_entry.details or {},
            ip_address=str(log_entry.ip_address) if log_entry.ip_address else None,
            user_agent=log_entry.user_agent or '',
            department_id=department_id,
            department_name=department_name or '',
            department_code=department_code or '',
        )
    except Exception:
        pass

    return log_entry
