from django.urls import path
from .views import *

urlpatterns = [
    path("request/", LoanRequestCreateView.as_view()),
    path("my-requests/", MyLoanRequestsView.as_view()),
    path("my-loans/", MyLoansView.as_view()),

    path("admin/pending/", AdminPendingLoansView.as_view()),
    path("admin/<uuid:pk>/approve/", ApproveLoanView.as_view()),
    path("admin/<uuid:pk>/reject/", RejectLoanView.as_view()),
]