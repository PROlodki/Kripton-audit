"""
Middleware для обновления last_seen (онлайн-статус пользователя).
"""
from django.utils import timezone
from kripton.models import UserActivity


class UserActivityMiddleware:
    """Обновляет UserActivity.last_seen при каждом запросе аутентифицированного пользователя."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                UserActivity.objects.update_or_create(
                    user=request.user,
                    defaults={'last_seen': timezone.now()},
                )
            except Exception:
                pass
        return response
