"""
API для дашбордов: сводка, данные для графиков, фильтрация.
"""
from django.utils import timezone
from django.db.models import Count
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from kripton.guide.models import Department
from .models import Report, ReportRequest, ReportType


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_report_request_queryset(self, request):
        """Заявки, доступные текущему пользователю (как в ReportRequestViewSet)."""
        user = request.user
        if user.is_superuser or user.is_staff:
            return ReportRequest.objects.all()
        from django.contrib.auth.models import Group
        if user.groups.filter(name='Менеджеры').exists():
            return ReportRequest.objects.all()
        qs = ReportRequest.objects.filter(requester=user)
        managed = Department.objects.filter(head_of_department=user)
        if managed.exists():
            qs = qs | ReportRequest.objects.filter(department__in=managed)
        st = ReportType.objects.filter(stakeholders=user)
        if st.exists():
            qs = qs | ReportRequest.objects.filter(report_type__in=st)
        return qs.distinct()

    def _get_report_queryset(self, request):
        """Отчёты, доступные текущему пользователю."""
        user = request.user
        if user.is_superuser or user.is_staff:
            return Report.objects.all()
        qs = Report.objects.filter(created_by=user)
        st = ReportType.objects.filter(stakeholders=user)
        if st.exists():
            qs = qs | Report.objects.filter(report_type__in=st)
        return qs.distinct()

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Сводка для первого экрана дашборда: счётчики заявок по статусам,
        отчётов, список подразделений и типов отчётов для меню.
        """
        rr_qs = self._get_report_request_queryset(request)
        report_qs = self._get_report_queryset(request)

        request_stats = {
            'total': rr_qs.count(),
            'pending': rr_qs.filter(status='pending').count(),
            'approved': rr_qs.filter(status='approved').count(),
            'rejected': rr_qs.filter(status='rejected').count(),
            'in_progress': rr_qs.filter(status='in_progress').count(),
            'completed': rr_qs.filter(status='completed').count(),
        }

        reports_total = report_qs.count()
        reports_submitted = report_qs.exclude(submitted_at__isnull=True).count()
        reports_approved = report_qs.exclude(approved_at__isnull=True).count()

        from kripton.permissions_services import PermissionService
        my_departments = PermissionService.get_user_departments(request.user)
        departments_data = [{'id': d.id, 'name': d.name, 'code': getattr(d, 'code', '') or ''} for d in my_departments]

        report_types = ReportType.objects.filter(is_active=True).values('id', 'name', 'code')[:50]

        return Response({
            'request_stats': request_stats,
            'reports_total': reports_total,
            'reports_submitted': reports_submitted,
            'reports_approved': reports_approved,
            'my_departments': departments_data,
            'report_types': list(report_types),
        })

    @action(detail=False, methods=['get'], url_path='charts')
    def charts(self, request):
        """
        Данные для графиков: заявки по дням (последние 30), по отделам, по типам отчётов,
        по статусам (pie).
        """
        rr_qs = self._get_report_request_queryset(request)
        days = min(90, max(7, int(request.query_params.get('days', 30))))

        # Заявки по дням (последние N дней)
        from django.db.models.functions import TruncDate
        start = timezone.now() - timezone.timedelta(days=days)
        by_date = (
            rr_qs.filter(created_at__gte=start)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        requests_by_day = [{'date': str(r['date']), 'count': r['count']} for r in by_date]

        # По отделам (топ)
        by_dept = (
            rr_qs.values('department_id', 'department__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        requests_by_department = [
            {'department_id': r['department_id'], 'department_name': r['department__name'] or '—', 'count': r['count']}
            for r in by_dept
        ]

        # По типам отчётов
        by_type = (
            rr_qs.values('report_type_id', 'report_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        requests_by_type = [
            {'report_type_id': r['report_type_id'], 'report_type_name': r['report_type__name'] or '—', 'count': r['count']}
            for r in by_type
        ]

        # По статусам (для круговой диаграммы)
        by_status = rr_qs.values('status').annotate(count=Count('id'))
        requests_by_status = [{'status': r['status'], 'count': r['count']} for r in by_status]

        return Response({
            'requests_by_day': requests_by_day,
            'requests_by_department': requests_by_department,
            'requests_by_type': requests_by_type,
            'requests_by_status': requests_by_status,
        })
