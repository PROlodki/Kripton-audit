from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .audit_views import AuditLogViewSet

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
]
