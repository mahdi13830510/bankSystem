from django.urls import path
from .views import (
    # customer
    LoanRequestCreateView,
    MyLoanRequestsView,
    MyLoanRequestDetailView,
    MyLoansView,
    MyLoanDetailView,
    # admin
    AdminLoanRequestListView,
    AdminLoanRequestDetailView,
    AdminPendingLoansView,
    EvaluateLoanRequestView,
    ApproveLoanView,
    RejectLoanView,
    AdminLoanListView,
    AdminLoanDetailView,
    AdminChangeLoanStatusView,
    AdminCustomerLoansView,
    AdminCustomerLoanRequestsView,
)

urlpatterns = [
    # ── Customer ──────────────────────────────────────────────
    path("request/",                        LoanRequestCreateView.as_view()),
    path("my-requests/",                    MyLoanRequestsView.as_view()),
    path("my-requests/<uuid:pk>/",          MyLoanRequestDetailView.as_view()),
    path("my-loans/",                       MyLoansView.as_view()),
    path("my-loans/<uuid:pk>/",             MyLoanDetailView.as_view()),

    # ── Admin: loan requests ───────────────────────────────────
    path("admin/requests/",                             AdminLoanRequestListView.as_view()),
    path("admin/requests/pending/",                     AdminPendingLoansView.as_view()),
    path("admin/requests/<uuid:pk>/",                   AdminLoanRequestDetailView.as_view()),
    path("admin/requests/<uuid:pk>/evaluate/",          EvaluateLoanRequestView.as_view()),
    path("admin/requests/<uuid:pk>/approve/",           ApproveLoanView.as_view()),
    path("admin/requests/<uuid:pk>/reject/",            RejectLoanView.as_view()),

    # ── Admin: loans ───────────────────────────────────────────
    path("admin/loans/",                                AdminLoanListView.as_view()),
    path("admin/loans/<uuid:pk>/",                      AdminLoanDetailView.as_view()),
    path("admin/loans/<uuid:pk>/status/",               AdminChangeLoanStatusView.as_view()),

    # ── Admin: by customer ─────────────────────────────────────
    path("admin/customer/<int:customer_id>/loans/",     AdminCustomerLoansView.as_view()),
    path("admin/customer/<int:customer_id>/requests/",  AdminCustomerLoanRequestsView.as_view()),
]