"""
Эндпоинты для фронтенда: сводка по пользователю, список доступных действий и URL.
"""
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response


class FrontendActionsAPIView(APIView):
    """
    GET /api/frontend/actions/
    Возвращает базовый URL API и список эндпоинтов для всех действий из шаблонов,
    чтобы фронт мог строить меню и запросы без хардкода.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        base = request.build_absolute_uri('/').rstrip('/')
        api_base = f"{base}/api"

        user = request.user
        is_staff = user.is_superuser or user.is_staff

        endpoints = {
            'auth': {
                'user': f'{api_base}/auth/user',
                'login': f'{api_base}/auth/users/login/',
            },
            'reports': {
                'list': f'{api_base}/reports/reports/',
                'detail': f'{api_base}/reports/reports/{{id}}/',
                'submit': f'{api_base}/reports/reports/{{id}}/submit/',
                'approve': f'{api_base}/reports/reports/{{id}}/approve/',
                'export': f'{api_base}/reports/reports/{{id}}/export/?format=xlsx',
                'validate': f'{api_base}/reports/reports/{{id}}/validate/',
                'history': f'{api_base}/reports/reports/{{id}}/history/',
                'check_access': f'{api_base}/reports/reports/{{id}}/check-access/',
            },
            'report_requests': {
                'list': f'{api_base}/reports/report-requests/',
                'detail': f'{api_base}/reports/report-requests/{{id}}/',
                'stats': f'{api_base}/reports/report-requests/stats/',
                'my_requests': f'{api_base}/reports/report-requests/my_requests/',
                'my_departments': f'{api_base}/reports/report-requests/my-departments/',
                'approve': f'{api_base}/reports/report-requests/{{id}}/approve/',
                'reject': f'{api_base}/reports/report-requests/{{id}}/reject/',
                'export': f'{api_base}/reports/report-requests/export/?format=csv',
            },
            'dashboard': {
                'summary': f'{api_base}/reports/dashboard/summary/',
                'charts': f'{api_base}/reports/dashboard/charts/',
            },
            'departments': {
                'list': f'{api_base}/reports/departments/',
                'detail': f'{api_base}/reports/departments/{{id}}/',
                'check_access': f'{api_base}/reports/departments/{{id}}/check-access/',
            },
            'report_types': {
                'list': f'{api_base}/reports/report-types/',
            },
            'personal_data': {
                'list': f'{api_base}/reports/personal-data/',
            },
            'audit': {
                'list': f'{api_base}/audit/logs/',
                'export': f'{api_base}/audit/logs/export/',
            },
            'datasources': {
                'list': f'{api_base}/datasources/',
                'preview': f'{api_base}/datasources/{{id}}/preview/',
                'load': f'{api_base}/datasources/{{id}}/load/',
                'status': f'{api_base}/datasources/{{id}}/status/',
                'test_connection': f'{api_base}/datasources/{{id}}/test_connection/',
            },
            'realtime': {
                'events': f'{api_base}/stream/events/',
                'online': f'{api_base}/stream/online/',
            },
        }

        # Краткая информация о пользователе
        user_info = {
            'id': user.pk,
            'username': getattr(user, 'username', ''),
            'email': getattr(user, 'email', ''),
            'is_staff': is_staff,
            'is_superuser': user.is_superuser,
        }

        return Response({
            'user': user_info,
            'endpoints': endpoints,
            'filters_docs': {
                'report_requests': '?status=...&department=...&report_type=...&search=...&ordering=...',
                'reports': '?report_type=...&created_by=...&search=...&ordering=...',
                'audit_logs': '?user=...&action_type=...&resource_type=...&date_from=...&date_to=...',
            },
        })
