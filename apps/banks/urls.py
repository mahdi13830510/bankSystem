from django.urls import path
from .views import *

urlpatterns = [
    path("", BankListView.as_view()),
    path("<uuid:pk>/", BankDetailView.as_view()),
    path("create/", BankCreateView.as_view()),
    path("<uuid:pk>/status/", BankStatusUpdateView.as_view()),
    path("<uuid:bank_id>/branches/", BranchListView.as_view()),
]