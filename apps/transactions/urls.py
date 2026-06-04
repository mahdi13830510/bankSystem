from django.urls import path
from .views import (
    # customer
    CardTransferView,
    IbanTransferView,
    StatementView,
    MyLimitUsageView,
    # admin
    AdminTransactionListView,
    AdminTransactionDetailView,
    AdminTransactionByReferenceView,
    AdminAccountStatementView,
    AdminReverseTransactionView,
    AdminResetLimitView,
    AdminLimitUsageView,
)

urlpatterns = [
    # ── Customer ──────────────────────────────────────────
    path("card-transfer/",                    CardTransferView.as_view()),
    path("iban-transfer/",                    IbanTransferView.as_view()),
    path("statement/<int:account_id>/",       StatementView.as_view()),
    path("limits/<int:account_id>/usage/",    MyLimitUsageView.as_view()),

    # ── Admin / Staff ──────────────────────────────────────
    path("admin/",                                          AdminTransactionListView.as_view()),
    path("admin/<uuid:pk>/",                                AdminTransactionDetailView.as_view()),
    path("admin/ref/<str:reference_number>/",               AdminTransactionByReferenceView.as_view()),
    path("admin/account/<int:account_id>/statement/",       AdminAccountStatementView.as_view()),
    path("admin/<uuid:pk>/reverse/",                        AdminReverseTransactionView.as_view()),
    path("admin/account/<int:account_id>/limits/reset/",    AdminResetLimitView.as_view()),
    path("admin/account/<int:account_id>/limits/usage/",    AdminLimitUsageView.as_view()),
]