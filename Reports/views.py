from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models

from .models import Department, ReportType, Report, ReportRequest
from .serializers import (
    DepartmentSerializer, 
    ReportTypeSerializer,
    ReportSerializer,
    ReportRequestSerializer,
    ReportRequestActionSerializer
)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


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
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        user = self.request.user
        
        # Администраторы видят все
        if user.is_superuser or user.is_staff:
            return Report.objects.all()
        
        # Обычные пользователи видят свои отчеты
        # и отчеты типов, где они заинтересованные лица
        queryset = Report.objects.filter(created_by=user)
        
        # Добавляем отчеты типов, где пользователь - заинтересованное лицо
        stakeholder_types = ReportType.objects.filter(stakeholders=user)
        if stakeholder_types.exists():
            queryset = queryset | Report.objects.filter(report_type__in=stakeholder_types)
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


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
        managed_departments = Department.objects.filter(head=user)
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
    def perform_action(self, request, pk=None):
        """Выполнить действие с запросом (утвердить/отклонить)"""
        report_request = self.get_object()
        serializer = ReportRequestActionSerializer(data=request.data)
        
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            user = request.user
            
            if action_type == 'approve':
                try:
                    report_request.approve(user)
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
