from django.urls import path
from .views import DataSourceListCreateView
# TODO "выдать" путь 
urlpatterns = [
    path('', DataSourceListCreateView.as_view()),
]
