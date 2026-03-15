from django.urls import path

from .views import (
    LoginAPIView, RegistrationAPIView, UserRetrieveUpdateAPIView,
    AdminCreateUserAPIView, AdminUserDetailAPIView,
)

app_name = 'authpage'
urlpatterns = [
    path('user', UserRetrieveUpdateAPIView.as_view()),
    path('users/', RegistrationAPIView.as_view()),
    path('users/login/', LoginAPIView.as_view()),
    path('admin/users/', AdminCreateUserAPIView.as_view()),
    path('admin/users/<int:pk>/', AdminUserDetailAPIView.as_view()),
]