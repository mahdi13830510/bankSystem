from django.urls import path

from .views import (
    MyAccountsView,
    AccountDetailView,
    OpenAccountView,
    DepositView,
    FreezeView,
    ActivateView,
    CloseView,
)

urlpatterns = [
    path("my/", MyAccountsView.as_view()),
    path("<int:pk>/", AccountDetailView.as_view()),
    path("open/", OpenAccountView.as_view()),

    path("<int:pk>/deposit/", DepositView.as_view()),

    path("<int:pk>/freeze/", FreezeView.as_view()),
    path("<int:pk>/activate/", ActivateView.as_view()),
    path("<int:pk>/close/", CloseView.as_view()),
]