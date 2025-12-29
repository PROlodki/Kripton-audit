from django.contrib import admin
from django.urls import path, include
from .views import index, admin, zl, user

urlpatterns = [
    path('auth/', index, name='index'),
    path('api/', include('kripton.authpage.urls', namespace='authpage')),
    path('admin/', admin, name='admin'),
    path('zl/', zl, name='zl'),
    path('user/', user, name='user'),
]
