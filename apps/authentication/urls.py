from django.urls import path

from .views import (
    LoginView,
    VerifyOTPView,
    LogoutView
)

urlpatterns = [
    path("login/", LoginView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("logout/", LogoutView.as_view()),
]