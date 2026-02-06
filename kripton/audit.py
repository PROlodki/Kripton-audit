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
):
    """
    Создать запись в логе аудита.

    :param request: HttpRequest (для user, ip_address, user_agent)
    :param action_type: строка из AuditLog.ActionType (create, update, delete, view, login, logout, approve, reject, other)
    :param resource_type: тип ресурса (например 'report', 'report_request', 'department')
    :param resource_id: идентификатор ресурса (строка или будет приведён к str)
    :param details: dict с дополнительными данными (сохраняется в JSON)
    :param user: пользователь (если не передан, берётся request.user)
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

    return AuditLog.objects.create(
        user=user,
        action_type=action_type,
        resource_type=str(resource_type)[:100] if resource_type else '',
        resource_id=str(resource_id)[:100] if resource_id else '',
        details=details,
        ip_address=ip,
        user_agent=user_agent,
    )
