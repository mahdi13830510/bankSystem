# apps/accounts/models.py

from django.db import models
from django.conf import settings
from apps.banks.models import Bank


class AccountType(models.TextChoices):
    SAVING = "SAVING", "Saving"
    CURRENT = "CURRENT", "Current"
    BUSINESS = "BUSINESS", "Business"


class CurrencyType(models.TextChoices):
    TRY = "TRY", "TRY"
    USD = "USD", "USD"
    EUR = "EUR", "EUR"


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    BLOCKED = "BLOCKED", "Blocked"
    CLOSED = "CLOSED", "Closed"


class Account(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts"
    )
    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="accounts"
    )

    account_number = models.CharField(max_length=20, unique=True)
    iban = models.CharField(max_length=34, unique=True)

    type = models.CharField(max_length=20, choices=AccountType.choices)
    currency = models.CharField(max_length=10, choices=CurrencyType.choices)

    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    blocked_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    loan_blocked_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False)
    class Meta:
        db_table = "accounts_account"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.account_number}"

    @property
    def available_balance(self):
        return self.balance - self.blocked_balance