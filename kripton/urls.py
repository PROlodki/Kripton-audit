from django.urls import path, include
from .views import index, admin, zl, user, logout_view

urlpatterns = [
    path('auth/', index, name='index'),
    path('logout/', logout_view, name='logout'),
    path('api/auth/', include('kripton.authpage.urls', namespace='authpage')),
    path('api/reports/', include('Reports.urls')),
    path('api/datasources/', include('kripton.datasources.urls')),
    path('api/guide/', include('kripton.guide.urls', namespace='guide')),
    path('api/audit/', include('kripton.audit_urls')),
    path('admin/', admin, name='admin'),
    path('zl/', zl, name='zl'),
    path('user/', user, name='user'),
]
