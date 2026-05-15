from django.urls import path
from .views import *

urlpatterns = [
    path("my/", MyInstallmentsView.as_view()),
    path("<uuid:pk>/pay/", PayInstallmentView.as_view()),
    path("loan/<uuid:loan_id>/remaining/", RemainingDebtView.as_view()),
]