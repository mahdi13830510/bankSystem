from django.urls import path
from .views import *

urlpatterns = [
    path("request/", LoanRequestCreateView.as_view()),
    path("my-requests/", MyLoanRequestsView.as_view()),
    path("my-loans/", MyLoansView.as_view()),
    # admin urls
    path("pending/", AdminPendingLoansView.as_view()),
    path("<uuid:pk>/approve/", ApproveLoanView.as_view()),
    path("<uuid:pk>/reject/", RejectLoanView.as_view()),
]
