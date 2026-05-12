from django.urls import path
from .views import (
    AccountListCreateAPIView,
    AccountDetailAPIView,
    FreezeAccountAPIView,
    UnfreezeAccountAPIView,
    DepositAPIView,
    WithdrawAPIView,
    BlockAmountAPIView,
    UnblockAmountAPIView,
    ChangeAccountOwnerAPIView,
    OwnershipHistoryListAPIView,
    MyAccountsAPIView,
)

urlpatterns = [
    # Accounts
    path("accounts/", AccountListCreateAPIView.as_view(), name="account-list-create"),
    path("accounts/<int:pk>/", AccountDetailAPIView.as_view(), name="account-detail"),

    # Status management
    path("accounts/<int:pk>/freeze/", FreezeAccountAPIView.as_view(), name="account-freeze"),
    path("accounts/<int:pk>/unfreeze/", UnfreezeAccountAPIView.as_view(), name="account-unfreeze"),

    # Balance operations
    path("accounts/<int:pk>/deposit/", DepositAPIView.as_view(), name="account-deposit"),
    path("accounts/<int:pk>/withdraw/", WithdrawAPIView.as_view(), name="account-withdraw"),
    path("accounts/<int:pk>/block/", BlockAmountAPIView.as_view(), name="account-block"),
    path("accounts/<int:pk>/unblock/", UnblockAmountAPIView.as_view(), name="account-unblock"),

    # Ownership
    path("accounts/<int:pk>/change-owner/", ChangeAccountOwnerAPIView.as_view(), name="account-change-owner"),
    path("accounts/<int:pk>/ownership-history/", OwnershipHistoryListAPIView.as_view(), name="account-ownership-history"),

    # Current user
    path("my-accounts/", MyAccountsAPIView.as_view(), name="my-accounts"),
]
