from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class AccountStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    PENDING = "pending", _("Pending")
    FROZEN = "frozen", _("Frozen")
    BLOCKED = "blocked", _("Blocked")
    CLOSED = "closed", _("Closed")
    DORMANT = "dormant", _("Dormant")


class AccountType(models.TextChoices):
    SAVINGS = "savings", _("Savings")
    CURRENT = "current", _("Current")
    SHORT_TERM = "short term", _("Short term")
    LONG_TERM = "long term", _("Long term")
    LOAN = "loan", _("Loan")
    DEPOSIT = "deposit", _("Deposit")
    CARD = "card", _("Card")


class CurrencyType(models.TextChoices):
    IRR = "IRR", _("IRR")
    IRT = "IRT", _("IRT")
    USD = "USD", _("USD")
    EUR = "EUR", _("EUR")


class Account(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounts",
        verbose_name=_("Customer"),
    )
    bank = models.ForeignKey(
        "banks.Bank",
        on_delete=models.PROTECT,
        related_name="accounts",
        verbose_name=_("Bank"),
    )
    account_number = models.CharField(_("Account Number"), max_length=20, unique=True, db_index=True)
    iban = models.CharField(_("IBAN"), max_length=34, unique=True, db_index=True)
    type = models.CharField(_("Type"), max_length=20, choices=AccountType.choices)
    currency = models.CharField(_("Currency"), max_length=10, choices=CurrencyType.choices, default=CurrencyType.IRR)
    balance = models.DecimalField(_("Balance"), max_digits=18, decimal_places=2, default=0,
                                  validators=[MinValueValidator(0)])
    blocked_balance = models.DecimalField(_("Blocked Balance"), max_digits=18, decimal_places=2, default=0,
                                          validators=[MinValueValidator(0)])
    status = models.CharField(_("Status"), max_length=20, choices=AccountStatus.choices, default=AccountStatus.PENDING)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    deleted_at = models.DateTimeField(_("Deleted At"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer", "bank"]),
            models.Index(fields=["bank", "status"]),
            models.Index(fields=["type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "bank", "type"],
                name="unique_account_type_per_customer_per_bank"
            )
        ]
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")

    def __str__(self):
        return f"{self.account_number} - {self.customer}"

    @property
    def available_balance(self):
        return self.balance - self.blocked_balance

    def is_active(self):
        return self.status == AccountStatus.ACTIVE

    def can_withdraw(self, amount):
        return amount > 0 and self.available_balance >= amount

    def soft_delete(self):
        self.status = AccountStatus.DELETED
        self.deleted_at = timezone.now()
        self.save(update_fields=["status", "deleted_at"])


class AccountOwnershipHistory(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="ownership_histories")
    old_customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="old_account_histories")
    new_customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="new_account_histories")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="changed_account_histories")
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = _("Account Ownership History")
        verbose_name_plural = _("Account Ownership Histories")

    def __str__(self):
        return f"{self.account} ownership changed"
