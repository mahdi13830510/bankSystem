from django.urls import path
from .views import (
    # customer
    MyInstallmentsView,
    MyInstallmentDetailView,
    MyLoanInstallmentsView,
    PayInstallmentView,
    RemainingDebtView,
    # admin
    AdminInstallmentListView,
    AdminInstallmentDetailView,
    AdminLoanInstallmentsView,
    AdminOverdueInstallmentsView,
    AdminApplyPenaltyView,
    AdminRemainingDebtView,
)

urlpatterns = [
    # ── Customer ────────────────────────────────────────────────────
    path("my/",                                     MyInstallmentsView.as_view()),
    path("my/<uuid:pk>/",                           MyInstallmentDetailView.as_view()),
    path("my/loan/<uuid:loan_id>/",                 MyLoanInstallmentsView.as_view()),
    path("<uuid:pk>/pay/",                          PayInstallmentView.as_view()),
    path("loan/<uuid:loan_id>/remaining/",          RemainingDebtView.as_view()),

    # ── Admin ────────────────────────────────────────────────────────
    path("admin/",                                  AdminInstallmentListView.as_view()),
    path("admin/overdue/",                          AdminOverdueInstallmentsView.as_view()),
    path("admin/<uuid:pk>/",                        AdminInstallmentDetailView.as_view()),
    path("admin/<uuid:pk>/penalty/",                AdminApplyPenaltyView.as_view()),
    path("admin/loan/<uuid:loan_id>/",              AdminLoanInstallmentsView.as_view()),
    path("admin/loan/<uuid:loan_id>/remaining/",    AdminRemainingDebtView.as_view()),
]