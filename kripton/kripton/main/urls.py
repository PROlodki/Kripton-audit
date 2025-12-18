from django.urls import path
from .views import index, admin, zl, user

urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin, name='admin'), 
    path('zl/', zl, name='zl'), 
    path('user/', user, name='user'),
]