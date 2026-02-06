from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import PersonalData, Department, ReportType, Report, ReportRequest
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
        queryset = Report.objects.filter(created_by=user)
        stakeholder_types = ReportType.objects.filter(stakeholders=user)
        if stakeholder_types.exists():
            queryset = queryset | Report.objects.filter(report_type__in=stakeholder_types)
        return queryset.distinct()
    
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
        if report.submitted_at:
            return Response(
                {'error': 'Отчет уже отправлен'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        report.submitted_at = timezone.now()
        report.save(update_fields=['submitted_at'])
        from kripton.audit import log_audit
        log_audit(
            request=request,
            action_type='other',
            resource_type='report',
            resource_id=str(report.pk),
            details={'title': report.title, 'action': 'submit'},
        )
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """ReportApproveView — утверждение отчета (для admin/ZL)."""
        report = self.get_object()
        user = request.user
        if not (user.is_superuser or user.is_staff):
            from django.contrib.auth.models import Group
            if not user.groups.filter(name__in=['Администраторы', 'Менеджеры']).exists():
                return Response(
                    {'error': 'Недостаточно прав для утверждения отчета'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        from django.utils import timezone
        report.approved_at = timezone.now()
        report.approved_by = user
        report.save(update_fields=['approved_at', 'approved_by'])
        from kripton.audit import log_audit
        log_audit(
            request=request,
            action_type='approve',
            resource_type='report',
            resource_id=str(report.pk),
            details={'title': report.title},
        )
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
        """ReportExportView — экспорт в PDF/Excel/Word (формат в query: format=pdf|xlsx|docx)."""
        report = self.get_object()
        fmt = (request.query_params.get('format') or 'xlsx').lower()
        if fmt not in ('pdf', 'xlsx', 'docx'):
            fmt = 'xlsx'
        from .export import export_report
        try:
            content_type, filename, content = export_report(report, fmt)
        except Exception as e:
            return Response(
                {'error': f'Ошибка экспорта: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        from django.http import HttpResponse
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


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
        
        # Администраторы и менеджеры видят все
        if user.is_superuser or user.is_staff:
            return ReportRequest.objects.all()
        
        # Проверяем группы
        from django.contrib.auth.models import Group
        is_manager = user.groups.filter(name='Менеджеры').exists()
        if is_manager:
            return ReportRequest.objects.all()
        
        # Обычный пользователь видит:
        # 1. Свои запросы
        # 2. Запросы своего отдела (если он руководитель)
        # 3. Запросы типов отчетов, где он заинтересованное лицо
        queryset = ReportRequest.objects.filter(requester=user)
        
        # Если пользователь - руководитель отдела
        managed_departments = Department.objects.filter(head_of_department=user)
        if managed_departments.exists():
            queryset = queryset | ReportRequest.objects.filter(department__in=managed_departments)
        
        # Если пользователь - заинтересованное лицо
        stakeholder_types = ReportType.objects.filter(stakeholders=user)
        if stakeholder_types.exists():
            queryset = queryset | ReportRequest.objects.filter(report_type__in=stakeholder_types)
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """ReportRequestApproveView — утверждение запроса (POST без body)."""
        report_request = self.get_object()
        try:
            report_request.approve(request.user)
            from kripton.audit import log_audit
            log_audit(request=request, action_type='approve', resource_type='report_request', resource_id=str(report_request.pk), details={'title': report_request.title})
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
                    from kripton.audit import log_audit
                    log_audit(
                        request=request,
                        action_type='approve',
                        resource_type='report_request',
                        resource_id=str(report_request.pk),
                        details={'title': report_request.title},
                    )
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