from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet,
    ReportTypeViewSet,
    ReportViewSet,
    ReportRequestViewSet
)

router = DefaultRouter()

# Регистрируем все ViewSet с указанием basename
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'report-types', ReportTypeViewSet, basename='report-type')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'report-requests', ReportRequestViewSet, basename='report-request')

urlpatterns = [
    path('', include(router.urls)),
]