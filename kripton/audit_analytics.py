from django.db.models import Count
from django.db.models.functions import TruncDate
from kripton.models import AuditLog
from Reports.models import ReportRequest
from django.utils import timezone
from datetime import timedelta


# =========================
# AUDIT ANALYTICS
# =========================

def get_user_activity(limit=10):
    return (
        AuditLog.objects
        .exclude(user__isnull=True)
        .values('user__username')
        .annotate(total=Count('id'))
        .order_by('-total')[:limit]
    )


def get_action_stats():
    """
    Статистика по типам действий (create, update, delete и т.д.)
    """
    return (
        AuditLog.objects
        .values('action_type')
        .annotate(total=Count('id'))
        .order_by('-total')
    )


def get_activity_by_day(days=30):
    since = timezone.now() - timedelta(days=days)

    return (
        AuditLog.objects
        .filter(timestamp__gte=since)
        .annotate(day=TruncDate('timestamp'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

# =========================
# REPORT ANALYTICS
# =========================

def get_report_status_stats():
    """
    Количество заявок по статусам
    """
    return (
        ReportRequest.objects
        .values('status')
        .annotate(total=Count('id'))
    )


def get_reports_by_department():
    """
    Количество заявок по подразделениям
    """
    return (
        ReportRequest.objects
        .values('department__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )


def get_reports_created_by_day(days=30):
    from django.utils import timezone
    from datetime import timedelta

    since = timezone.now() - timedelta(days=days)

    return (
        ReportRequest.objects
        .filter(created_at__gte=since)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )