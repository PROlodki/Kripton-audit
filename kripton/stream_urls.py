from django.urls import path
from .streaming_views import ServerSentEventsView, OnlineUsersAPIView

urlpatterns = [
    path('events/', ServerSentEventsView.as_view(), name='stream-events'),
    path('online/', OnlineUsersAPIView.as_view(), name='stream-online'),
]
