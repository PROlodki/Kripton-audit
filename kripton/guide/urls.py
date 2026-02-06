from django.urls import path
from .views import DepartmentListCreateAPIView, DepartmentDetailAPIView

app_name = 'guide'
urlpatterns = [
    path('departments/', DepartmentListCreateAPIView.as_view(), name='department-list-create'),
    path('departments/<int:pk>/', DepartmentDetailAPIView.as_view(), name='department-detail'),
]
