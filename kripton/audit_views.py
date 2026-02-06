"""
API лога аудита: список с фильтрацией и экспорт.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import AuditLog
from .audit_serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    AuditLogListView — список логов с фильтрацией.
    Фильтры: user, action_type, resource_type, resource_id, date_from, date_to.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'action_type', 'resource_type']
    
    def get_queryset(self):
        qs = AuditLog.objects.all().select_related('user').order_by('-timestamp')
        user = self.request.user
        if not (user.is_superuser or user.is_staff):
            qs = qs.filter(user=user)
        # Доп. фильтры из query params
        resource_id = self.request.query_params.get('resource_id')
        if resource_id is not None:
            qs = qs.filter(resource_id=resource_id)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                from django.utils.dateparse import parse_datetime
                dt = parse_datetime(date_from) or timezone.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                qs = qs.filter(timestamp__gte=dt)
            except Exception:
                pass
        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                from django.utils.dateparse import parse_datetime
                dt = parse_datetime(date_to) or timezone.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                qs = qs.filter(timestamp__lte=dt)
            except Exception:
                pass
        return qs
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        AuditLogExportView — экспорт логов (CSV по тем же фильтрам).
        """
        qs = self.get_queryset()[:10000]
        import csv
        from io import StringIO
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            'id', 'timestamp', 'user_email', 'action_type', 'resource_type', 'resource_id',
            'ip_address', 'user_agent', 'details',
        ])
        for log in qs:
            writer.writerow([
                log.id,
                log.timestamp.isoformat() if log.timestamp else '',
                log.user.email if log.user else '',
                log.action_type,
                log.resource_type or '',
                log.resource_id or '',
                str(log.ip_address) if log.ip_address else '',
                (log.user_agent or '')[:200],
                str(log.details)[:500],
            ])
        buf.seek(0)
        from django.http import HttpResponse
        response = HttpResponse(buf.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="audit_log.csv"'
        return response
