from django.urls import path
from .views import (
    # customer
    MyAccountsView,
    AccountDetailView,
    OpenAccountView,
    SetPrimaryAccountView,
    # staff: status & balance ops
    DepositView,
    WithdrawView,
    FreezeView,
    ActivateView,
    CloseView,
    # admin: list & detail
    AdminAccountListView,
    AdminAccountDetailView,
    AdminAccountByNumberView,
    AdminAccountByIBANView,
    AdminCustomerAccountsView,
    AdminOpenAccountView,
    AdminSetPrimaryAccountView,
    # admin: balance ops
    BlockBalanceView,
    UnblockBalanceView,
    # admin: stats
    AdminAccountStatsView,
)

urlpatterns = [
    # ── Customer ────────────────────────────────────────────────────
    path("my/",                             MyAccountsView.as_view()),
    path("open/",                           OpenAccountView.as_view()),
    path("<int:pk>/",                       AccountDetailView.as_view()),
    path("<int:pk>/set-primary/",           SetPrimaryAccountView.as_view()),

    # ── Staff: عملیات روی حساب ────────────────────────────────────
    path("<int:pk>/deposit/",               DepositView.as_view()),
    path("<int:pk>/withdraw/",              WithdrawView.as_view()),
    path("<int:pk>/freeze/",                FreezeView.as_view()),
    path("<int:pk>/activate/",              ActivateView.as_view()),
    path("<int:pk>/close/",                 CloseView.as_view()),

    # ── Admin: list & search ───────────────────────────────────────
    path("admin/",                                          AdminAccountListView.as_view()),
    path("admin/stats/",                                    AdminAccountStatsView.as_view()),
    path("admin/open/",                                     AdminOpenAccountView.as_view()),
    path("admin/<int:pk>/",                                 AdminAccountDetailView.as_view()),
    path("admin/<int:pk>/set-primary/",                     AdminSetPrimaryAccountView.as_view()),
    path("admin/number/<str:account_number>/",              AdminAccountByNumberView.as_view()),
    path("admin/iban/<str:iban>/",                          AdminAccountByIBANView.as_view()),
    path("admin/customer/<int:customer_id>/",               AdminCustomerAccountsView.as_view()),

    # ── Admin: balance ops ─────────────────────────────────────────
    path("admin/<int:pk>/block-balance/",                   BlockBalanceView.as_view()),
    path("admin/<int:pk>/unblock-balance/",                 UnblockBalanceView.as_view()),
]