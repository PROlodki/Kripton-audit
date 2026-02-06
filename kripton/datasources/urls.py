from django.urls import path
from .views import DataSourceListCreateView, PreviewView

urlpatterns = [
    path('', DataSourceListCreateView.as_view()),
    path('<int:pk>/preview/', PreviewView.as_view(), name='datasource-preview'),
]
