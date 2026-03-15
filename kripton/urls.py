from django.urls import path, include
from .views import index, logout_view, dashboard, admin, zl, user
from .frontend_views import FrontendActionsAPIView

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('auth/', index, name='index'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('api/auth/', include('kripton.authpage.urls', namespace='authpage')),
    path('api/reports/', include('Reports.urls')),
    path('api/datasources/', include('kripton.datasources.urls')),
    path('api/guide/', include('kripton.guide.urls', namespace='guide')),
    path('api/audit/', include('kripton.audit_urls')),
    path('api/frontend/actions/', FrontendActionsAPIView.as_view(), name='frontend-actions'),
    path('api/stream/', include('kripton.stream_urls')),
    path('admin/', admin, name='admin'),
    path('zl/', zl, name='zl'),
    path('user/', user, name='user'),
]
