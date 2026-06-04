from django.urls import path
from .views import (
    # customer
    MyNotificationsView,
    MarkAsReadView,
    MarkAllAsReadView,
    UnreadCountView,
    # admin
    AdminNotificationListView,
    AdminUserNotificationsView,
    AdminSendNotificationView,
    AdminBroadcastView,
    AdminDeleteNotificationView,
)

urlpatterns = [
    # ── Customer ──────────────────────────────
    path("my/", MyNotificationsView.as_view()),
    path("unread-count/", UnreadCountView.as_view()),
    path("mark-all-read/", MarkAllAsReadView.as_view()),
    path("<uuid:pk>/read/", MarkAsReadView.as_view()),

    # ── Admin / Staff ──────────────────────────
    path("admin/", AdminNotificationListView.as_view()),
    path("admin/send/", AdminSendNotificationView.as_view()),
    path("admin/broadcast/", AdminBroadcastView.as_view()),
    path("admin/user/<int:user_id>/", AdminUserNotificationsView.as_view()),
    path("admin/<uuid:pk>/delete/", AdminDeleteNotificationView.as_view()),
]
