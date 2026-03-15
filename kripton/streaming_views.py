"""
SSE (Server-Sent Events) и API онлайн-пользователей.
"""
import json
import time
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from kripton.models import RealtimeEvent, UserActivity


def _sse_message(event: str, data: dict) -> str:
    """Формирование одного SSE-сообщения."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ServerSentEventsView(APIView):
    """
    GET /api/stream/events/
    Поток событий в формате SSE. Клиент подключается и получает новые события
    (смена статуса отчёта, уведомления). Интервал опроса на сервере 2 сек.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        def event_stream():
            user = request.user
            last_id = 0
            # Таймаут потока ~5 минут, затем клиент переподключится
            deadline = time.time() + 300
            while time.time() < deadline:
                events = RealtimeEvent.objects.filter(
                    user=user, read=False, id__gt=last_id
                ).order_by('id')[:50]
                for ev in events:
                    yield _sse_message(ev.event_type, {
                        'id': ev.id,
                        'payload': ev.payload,
                        'created_at': ev.created_at.isoformat() if ev.created_at else None,
                    })
                    last_id = max(last_id, ev.id)
                    ev.read = True
                    ev.save(update_fields=['read'])
                time.sleep(2)

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class OnlineUsersAPIView(APIView):
    """
    GET /api/stream/online/
    Список пользователей, активных за последние 5 минут (last_seen обновляется middleware).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        threshold = timezone.now() - timezone.timedelta(minutes=5)
        activity = UserActivity.objects.filter(last_seen__gte=threshold).select_related('user')
        user_ids = list(activity.values_list('user_id', flat=True))
        users = User.objects.filter(pk__in=user_ids).values('id', 'username', 'email')
        last_seen_map = {a.user_id: a.last_seen for a in activity}
        result = [
            {
                'id': u['id'],
                'username': u['username'],
                'email': u.get('email', ''),
                'last_seen': last_seen_map.get(u['id']).isoformat() if last_seen_map.get(u['id']) else None,
            }
            for u in users
        ]
        return Response({'online': result})
