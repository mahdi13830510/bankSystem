from django.urls import path
from .views import *

urlpatterns = [
    path("my/", MyNotificationsView.as_view()),
    path("<uuid:pk>/read/", MarkAsReadView.as_view()),
    path("unread-count/", UnreadCountView.as_view()),
]