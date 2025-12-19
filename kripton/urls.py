from django.contrib import admin
from django.urls import path, include
from .views import index, admin, zl, user

urlpatterns = [
    path('auth/', index, name='index'),
    path('admin/', admin, name='admin'), 
    path('zl/', zl, name='zl'), 
    path('user/', user, name='user'),
]
