from django.urls import path
from .views import (
    # public / auth flow
    LoginView,
    VerifyOTPView,
    RefreshTokenView,
    LogoutView,
    # customer sessions
    MySessionsView,
    RevokeMySessionView,
    RevokeOtherSessionsView,
    # admin sessions
    AdminSessionListView,
    AdminSessionDetailView,
    AdminRevokeSessionView,
    AdminUserSessionsView,
    AdminRevokeAllUserSessionsView,
    # admin OTP
    AdminUserOTPListView,
    AdminInvalidateUserOTPsView,
)

urlpatterns = [
    # ── Public / Auth flow ─────────────────────────────────────
    path("login/",          LoginView.as_view()),
    path("verify-otp/",     VerifyOTPView.as_view()),
    path("refresh/",        RefreshTokenView.as_view()),
    path("logout/",         LogoutView.as_view()),

    # ── Customer  ─────────────────────────────
    path("sessions/my/",                    MySessionsView.as_view()),
    path("sessions/my/<int:pk>/revoke/",    RevokeMySessionView.as_view()),
    path("sessions/revoke-others/",         RevokeOtherSessionsView.as_view()),

    # ── Admin: sessions ────────────────────────────────────────
    path("admin/sessions/",                             AdminSessionListView.as_view()),
    path("admin/sessions/<int:pk>/",                    AdminSessionDetailView.as_view()),
    path("admin/sessions/<int:pk>/revoke/",             AdminRevokeSessionView.as_view()),
    path("admin/users/<int:user_id>/sessions/",         AdminUserSessionsView.as_view()),
    path("admin/users/<int:user_id>/sessions/revoke-all/", AdminRevokeAllUserSessionsView.as_view()),

    # ── Admin: OTP ─────────────────────────────────────────────
    path("admin/users/<int:user_id>/otps/",             AdminUserOTPListView.as_view()),
    path("admin/users/<int:user_id>/otps/invalidate/",  AdminInvalidateUserOTPsView.as_view()),
]