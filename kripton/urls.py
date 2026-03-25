from django.contrib import admin
from django.urls import path, include
from .views import index, admin, zl, user
from .views import index, logout_view, dashboard, admin, zl, user
from .frontend_views import FrontendActionsAPIView
from kripton.analytics_views import AnalyticsView

urlpatterns = [
    path('analytics/', AnalyticsView.as_view()),
    path('', dashboard, name='dashboard'),
    path('auth/', index, name='index'),
    path('api/', include('kripton.authpage.urls', namespace='authpage')),
    path('admin/', admin, name='admin'),
    path('zl/', zl, name='zl'),
    path('user/', user, name='user'),
]
