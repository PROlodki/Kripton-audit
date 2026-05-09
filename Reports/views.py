from django.db.models import Q
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from kripton.guide.models import Department
from .models import PersonalData, ReportType, Report, ReportRequest
from .services import ReportService
from kripton.permissions_services import PermissionService
from .serializers import (
    DepartmentSerializer,
    ReportTypeSerializer,
    ReportSerializer,
    ReportListSerializer,
    ReportRequestSerializer,
    ReportRequestActionSerializer,
    PersonalDataSerializer,
)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'code']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """DepartmentUsersView — пользователи (персонал) подразделения."""
        department = self.get_object()
        from .models import PersonalData
        qs = PersonalData.objects.filter(department=department)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PersonalDataSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = PersonalDataSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def reports(self, request, pk=None):
        """DepartmentReportsView — отчёты подразделения (через запросы)."""
        department = self.get_object()
        report_ids = ReportRequest.objects.filter(department=department).exclude(
            report_id__isnull=True
        ).values_list('report_id', flat=True)
        qs = Report.objects.filter(pk__in=report_ids)
        page = self.paginate_queryset(qs)
        serializer_class = ReportListSerializer if request.query_params.get('brief') else ReportSerializer
        if page is not None:
            serializer = serializer_class(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = serializer_class(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='check-access')
    def check_access(self, request, pk=None):
        """Проверка доступа к подразделению (PermissionService.check_department_access)."""
        department = self.get_object()
        can = PermissionService.check_department_access(request.user, department)
        return Response({'can_access': can})


class ReportTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ReportTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return ReportType.objects.all()
        return ReportType.objects.filter(is_active=True)
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'created_by']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'submitted_at', 'approved_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        return ReportSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return Report.objects.all()
        # Заинтересованное лицо: отчёты только по своим типам (не видит отчёты других ЗЛ)
        stakeholder_types = ReportType.objects.filter(stakeholders=user)
        if stakeholder_types.exists():
            return Report.objects.filter(report_type__in=stakeholder_types).distinct()
        # Обычный пользователь: только свои отчёты и отчёты по заявкам, назначенным ему
        return Report.objects.filter(
            Q(created_by=user) | Q(source_request__assigned_to=user)
        ).distinct()

    @action(detail=True, methods=['get'], url_path='check-access')
    def check_access(self, request, pk=None):
        """Проверка доступа к отчёту (PermissionService.check_report_access)."""
        report = self.get_object()
        can = PermissionService.check_report_access(request.user, report)
        return Response({'can_access': can})
    
    def perform_create(self, serializer):
        report = serializer.save(created_by=self.request.user)
        from kripton.audit import log_audit
        log_audit(
            request=self.request,
            action_type='create',
            resource_type='report',
            resource_id=str(report.pk),
            details={'title': report.title},
        )
    
    def perform_update(self, serializer):
        report = serializer.save()
        from kripton.audit import log_audit
        log_audit(
            request=self.request,
            action_type='update',
            resource_type='report',
            resource_id=str(report.pk),
            details={'title': report.title},
        )
    
    def perform_destroy(self, instance):
        pk, title = instance.pk, instance.title
        instance.delete()
        from kripton.audit import log_audit
        log_audit(
            request=self.request,
            action_type='delete',
            resource_type='report',
            resource_id=str(pk),
            details={'title': title},
        )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """ReportSubmitView — отправка отчета."""
        report = self.get_object()
        try:
            ReportService.submit_report(report)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        from kripton.audit import log_audit
        log_audit(
            request=request,
            action_type='other',
            resource_type='report',
            resource_id=str(report.pk),
            details={'title': report.title, 'action': 'submit'},
        )
        try:
            from kripton.realtime_services import notify_report_status
            notify_report_status(report, 'report_submitted', {'by': request.user.username})
        except Exception:
            pass
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """ReportApproveView — утверждение отчета (для admin/ZL)."""
        report = self.get_object()
        user = request.user
        if not (user.is_superuser or user.is_staff):
            from django.contrib.auth.models import Group
            if not user.groups.filter(name__in=['Менеджеры']).exists(): # Убрал 'Администраторы' из тех кто может утвердить отчет
                return Response(
                    {'error': 'Недостаточно прав для утверждения отчета'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        ReportService.approve_report(report, user)
        from kripton.audit import log_audit
        log_audit(
            request=request,
            action_type='approve',
            resource_type='report',
            resource_id=str(report.pk),
            details={'title': report.title},
        )
        try:
            from kripton.realtime_services import notify_report_status
            notify_report_status(report, 'report_approved', {'by': user.username})
        except Exception:
            pass
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """ReportHistoryView — история изменений отчета (из AuditLog)."""
        report = self.get_object()
        from kripton.models import AuditLog
        logs = AuditLog.objects.filter(
            resource_type='report',
            resource_id=str(report.pk),
        ).order_by('-timestamp')[:100]
        from kripton.audit_serializers import AuditLogSerializer
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """ReportExportView — экспорт в Excel/Word (формат в query: format=xlsx|docx)."""
        report = self.get_object()
        fmt = (request.query_params.get('format') or 'xlsx').lower()
        if fmt not in ('xlsx', 'docx'):
            fmt = 'xlsx'
        try:
            if fmt == 'docx':
                content_type, filename, content = ReportService.generate_word(report)
            else:
                content_type, filename, content = ReportService.generate_excel(report)
        except Exception as e:
            return Response(
                {'error': f'Ошибка экспорта: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        from django.http import HttpResponse
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='validate')
    def validate_report(self, request, pk=None):
        """ReportValidateView — валидация данных отчёта."""
        report = self.get_object()
        ok, errors = ReportService.validate_report(report)
        return Response({'valid': ok, 'errors': errors})

    @action(detail=False, methods=['get'], url_path='export')
    def export_list(self, request):
        """
        Экспорт списка отчётов (с учётом фильтров) в CSV или Excel.
        Query: format=csv | xlsx.
        """
        queryset = self.get_queryset()[:5000]
        fmt = (request.query_params.get('format') or 'csv').lower()
        if fmt not in ('csv', 'xlsx'):
            fmt = 'csv'
        if fmt == 'csv':
            import csv
            from io import StringIO
            buf = StringIO()
            writer = csv.writer(buf)
            writer.writerow(['id', 'title', 'report_type', 'created_by', 'created_at', 'submitted_at', 'approved_at'])
            for r in queryset.select_related('report_type', 'created_by'):
                writer.writerow([
                    r.id, r.title, r.report_type.name if r.report_type_id else '',
                    getattr(r.created_by, 'username', ''), r.created_at.isoformat() if r.created_at else '',
                    r.submitted_at.isoformat() if r.submitted_at else '', r.approved_at.isoformat() if r.approved_at else '',
                ])
            buf.seek(0)
            from django.http import HttpResponse
            resp = HttpResponse(buf.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8-sig')
            resp['Content-Disposition'] = 'attachment; filename="reports.csv"'
            return resp
        try:
            import openpyxl
            from io import BytesIO
        except ImportError:
            return Response({'error': 'Установите openpyxl для экспорта в Excel'}, status=status.HTTP_501_NOT_IMPLEMENTED)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Отчёты'
        for col, h in enumerate(['id', 'title', 'report_type', 'created_by', 'created_at', 'submitted_at', 'approved_at'], 1):
            ws.cell(row=1, column=col, value=h)
        for row_idx, r in enumerate(queryset.select_related('report_type', 'created_by'), 2):
            ws.cell(row=row_idx, column=1, value=r.id)
            ws.cell(row=row_idx, column=2, value=r.title)
            ws.cell(row=row_idx, column=3, value=r.report_type.name if r.report_type_id else '')
            ws.cell(row=row_idx, column=4, value=getattr(r.created_by, 'username', ''))
            ws.cell(row=row_idx, column=5, value=r.created_at.isoformat() if r.created_at else '')
            ws.cell(row=row_idx, column=6, value=r.submitted_at.isoformat() if r.submitted_at else '')
            ws.cell(row=row_idx, column=7, value=r.approved_at.isoformat() if r.approved_at else '')
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        from django.http import HttpResponse
        resp = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="reports.xlsx"'
        return resp


class ReportRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'department', 'report_type', 'priority']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'deadline']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user

        # Админ: все заявки
        if user.is_superuser or user.is_staff:
            return ReportRequest.objects.all()
        from django.contrib.auth.models import Group
        if user.groups.filter(name='Менеджеры').exists():
            return ReportRequest.objects.all()

        # Заинтересованное лицо: только заявки по типам отчётов, где он ЗЛ (не видит данные других ЗЛ)
        stakeholder_types = ReportType.objects.filter(stakeholders=user)
        if stakeholder_types.exists():
            return ReportRequest.objects.filter(report_type__in=stakeholder_types).distinct()

        # Обычный пользователь (исполнитель): только заявки, назначенные ему (не видит задания коллег)
        return ReportRequest.objects.filter(assigned_to=user)
    
    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """ReportRequestApproveView — утверждение запроса (POST без body)."""
        report_request = self.get_object()
        try:
            report_request.approve(request.user)
            if request.user.is_staff or request.user.is_superuser:
                aid = request.data.get('assigned_to')
                if aid is not None:
                    from kripton.authpage.models import User as AuthUser
                    report_request.assigned_to = AuthUser.objects.filter(pk=aid).first()
                    report_request.save(update_fields=['assigned_to'])
            from kripton.audit import log_audit
            log_audit(request=request, action_type='approve', resource_type='report_request', resource_id=str(report_request.pk), details={'title': report_request.title})
            try:
                from kripton.realtime_services import notify_report_request_status
                notify_report_request_status(report_request, 'request_approved')
            except Exception:
                pass
            return Response({'message': 'Запрос утвержден', 'status': report_request.status}, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонение запроса (POST body: rejection_reason)."""
        report_request = self.get_object()
        reason = request.data.get('rejection_reason', '')
        try:
            report_request.reject(request.user, rejection_reason=reason)
            from kripton.audit import log_audit
            log_audit(request=request, action_type='reject', resource_type='report_request', resource_id=str(report_request.pk), details={'title': report_request.title, 'rejection_reason': reason})
            try:
                from kripton.realtime_services import notify_report_request_status
                notify_report_request_status(report_request, 'request_rejected', {'rejection_reason': reason})
            except Exception:
                pass
            return Response({'message': 'Запрос отклонен', 'status': report_request.status}, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['post'])
    def perform_action(self, request, pk=None):
        """Выполнить действие с запросом (утвердить/отклонить) — body: {action, rejection_reason?}"""
        report_request = self.get_object()
        serializer = ReportRequestActionSerializer(data=request.data)
        
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            user = request.user
            
            if action_type == 'approve':
                try:
                    report_request.approve(user)
                    if user.is_staff or user.is_superuser:
                        report_request.assigned_to = serializer.validated_data.get('assigned_to')
                        report_request.save(update_fields=['assigned_to'])
                    from kripton.audit import log_audit
                    log_audit(
                        request=request,
                        action_type='approve',
                        resource_type='report_request',
                        resource_id=str(report_request.pk),
                        details={'title': report_request.title},
                    )
                    try:
                        from kripton.realtime_services import notify_report_request_status
                        notify_report_request_status(report_request, 'request_approved')
                    except Exception:
                        pass
                    return Response(
                        {'message': 'Запрос утвержден', 'status': report_request.status},
                        status=status.HTTP_200_OK
                    )
                except PermissionError as e:
                    return Response(
                        {'error': str(e)},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            elif action_type == 'reject':
                try:
                    rejection_reason = serializer.validated_data.get('rejection_reason', '')
                    report_request.reject(user, rejection_reason=rejection_reason)
                    from kripton.audit import log_audit
                    log_audit(
                        request=request,
                        action_type='reject',
                        resource_type='report_request',
                        resource_id=str(report_request.pk),
                        details={'title': report_request.title, 'rejection_reason': rejection_reason},
                    )
                    try:
                        from kripton.realtime_services import notify_report_request_status
                        notify_report_request_status(report_request, 'request_rejected', {'rejection_reason': rejection_reason})
                    except Exception:
                        pass
                    return Response(
                        {'message': 'Запрос отклонен', 'status': report_request.status},
                        status=status.HTTP_200_OK
                    )
                except PermissionError as e:
                    return Response(
                        {'error': str(e)},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика по запросам"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'in_progress': queryset.filter(status='in_progress').count(),
            'completed': queryset.filter(status='completed').count(),
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Только мои запросы"""
        queryset = self.get_queryset().filter(requester=request.user)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-departments')
    def my_departments(self, request):
        """Подразделения текущего пользователя (PermissionService.get_user_departments)."""
        departments = PermissionService.get_user_departments(request.user)
        from .serializers import DepartmentSerializer
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='export')
    def export_list(self, request):
        """
        Экспорт списка заявок (с учётом фильтров) в CSV или Excel.
        Query: format=csv | xlsx (по умолчанию csv).
        """
        queryset = self.get_queryset()[:5000]
        fmt = (request.query_params.get('format') or 'csv').lower()
        if fmt not in ('csv', 'xlsx'):
            fmt = 'csv'

        if fmt == 'csv':
            import csv
            from io import StringIO
            buf = StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                'id', 'title', 'requester', 'department', 'report_type', 'status',
                'created_at', 'approved_at', 'deadline', 'priority',
            ])
            for r in queryset.select_related('requester', 'department', 'report_type'):
                writer.writerow([
                    r.id, r.title, getattr(r.requester, 'username', ''),
                    r.department.name if r.department_id else '',
                    r.report_type.name if r.report_type_id else '',
                    r.status, r.created_at.isoformat() if r.created_at else '',
                    r.approved_at.isoformat() if r.approved_at else '',
                    r.deadline.isoformat() if r.deadline else '', r.priority or '',
                ])
            buf.seek(0)
            from django.http import HttpResponse
            resp = HttpResponse(buf.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8-sig')
            resp['Content-Disposition'] = 'attachment; filename="report_requests.csv"'
            return resp

        # xlsx
        try:
            import openpyxl
            from io import BytesIO
        except ImportError:
            return Response(
                {'error': 'Для экспорта в Excel установите openpyxl'},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Заявки'
        headers = ['id', 'title', 'requester', 'department', 'report_type', 'status', 'created_at', 'approved_at', 'deadline', 'priority']
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        for row_idx, r in enumerate(queryset.select_related('requester', 'department', 'report_type'), 2):
            ws.cell(row=row_idx, column=1, value=r.id)
            ws.cell(row=row_idx, column=2, value=r.title)
            ws.cell(row=row_idx, column=3, value=getattr(r.requester, 'username', ''))
            ws.cell(row=row_idx, column=4, value=r.department.name if r.department_id else '')
            ws.cell(row=row_idx, column=5, value=r.report_type.name if r.report_type_id else '')
            ws.cell(row=row_idx, column=6, value=r.status)
            ws.cell(row=row_idx, column=7, value=r.created_at.isoformat() if r.created_at else '')
            ws.cell(row=row_idx, column=8, value=r.approved_at.isoformat() if r.approved_at else '')
            ws.cell(row=row_idx, column=9, value=r.deadline.isoformat() if r.deadline else '')
            ws.cell(row=row_idx, column=10, value=r.priority or '')
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        from django.http import HttpResponse
        resp = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="report_requests.xlsx"'
        return resp


class PersonalDataViewSet(viewsets.ModelViewSet):
    queryset = PersonalData.objects.all()
    serializer_class = PersonalDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['last_name', 'first_name', 'middle_name', 'position', 'rank']
    ordering_fields = ['last_name', 'hire_date', 'created_at']
    ordering = ['last_name', 'first_name']
    
    def get_queryset(self):
        user = self.request.user
        
        # Администраторы видят все
        if user.is_superuser or user.is_staff:
            return PersonalData.objects.all()
        
        # Руководители видят сотрудников своего отдела
        managed_departments = Department.objects.filter(head_of_department=user)
        if managed_departments.exists():
            return PersonalData.objects.filter(department__in=managed_departments)
        
        # Обычные пользователи видят только свои данные
        return PersonalData.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Только активные сотрудники"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_department(self, request):
        """Сотрудники по отделам"""
        department_id = request.query_params.get('department_id')
        if department_id:
            queryset = self.get_queryset().filter(department_id=department_id)
        else:
            queryset = self.get_queryset()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)