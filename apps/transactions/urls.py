from django.urls import path
from .views import (
    CardTransferView,
    IbanTransferView,
    StatementView
)

urlpatterns = [
    path("card-transfer/", CardTransferView.as_view()),
    path("iban-transfer/", IbanTransferView.as_view()),
    path("statement/<uuid:account_id>/", StatementView.as_view()),
]