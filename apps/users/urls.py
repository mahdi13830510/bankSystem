from django.urls import path
from .views import (
    # public
    RegisterView,
    # customer
    MeView,
    ChangePasswordView,
    MyProfileView,
    MyDevicesView,
    DeleteMyDeviceView,
    # admin
    AdminUserListView,
    AdminUserDetailView,
    AdminVerifyUserView,
    AdminBlockUserView,
    AdminUnblockUserView,
    AdminSuspendUserView,
    AdminActivateUserView,
    AdminChangeRoleView,
    AdminResetFailedAttemptsView,
    AdminResetPasswordView,
    AdminUserProfileView,
    AdminUserDevicesView,
    AdminDeleteDeviceView,
)

urlpatterns = [
    # ── Public ─────────────────────────────────────────────────
    path("register/",                           RegisterView.as_view()),

    # ── Customer  ────────────────────────────────────
    path("me/",                                 MeView.as_view()),
    path("me/change-password/",                 ChangePasswordView.as_view()),
    path("me/profile/",                         MyProfileView.as_view()),
    path("me/devices/",                         MyDevicesView.as_view()),
    path("me/devices/<int:pk>/",                DeleteMyDeviceView.as_view()),

    # ── Admin: list & detail ────────────────────────────────────
    path("admin/",                              AdminUserListView.as_view()),
    path("admin/<int:pk>/",                     AdminUserDetailView.as_view()),

    # ── Admin: status actions ───────────────────────────────────
    path("admin/<int:pk>/verify/",              AdminVerifyUserView.as_view()),
    path("admin/<int:pk>/block/",               AdminBlockUserView.as_view()),
    path("admin/<int:pk>/unblock/",             AdminUnblockUserView.as_view()),
    path("admin/<int:pk>/suspend/",             AdminSuspendUserView.as_view()),
    path("admin/<int:pk>/activate/",            AdminActivateUserView.as_view()),

    # ── Admin: role & security ──────────────────────────────────
    path("admin/<int:pk>/change-role/",         AdminChangeRoleView.as_view()),
    path("admin/<int:pk>/reset-attempts/",      AdminResetFailedAttemptsView.as_view()),
    path("admin/<int:pk>/reset-password/",      AdminResetPasswordView.as_view()),

    # ── Admin: profile & devices ────────────────────────────────
    path("admin/<int:pk>/profile/",             AdminUserProfileView.as_view()),
    path("admin/<int:pk>/devices/",             AdminUserDevicesView.as_view()),
    path("admin/<int:pk>/devices/<int:device_pk>/", AdminDeleteDeviceView.as_view()),
]