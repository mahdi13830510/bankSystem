import uuid
from decimal import Decimal
from django.db import models


class TransactionType(models.TextChoices):
    CARD_TO_CARD = "CARD_TO_CARD", "Card To Card"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER", "Internal Transfer"
    IBAN_TRANSFER = "IBAN_TRANSFER", "IBAN Transfer"
    CASH_DEPOSIT = "CASH_DEPOSIT", "Cash Deposit"
    CASH_WITHDRAW = "CASH_WITHDRAW", "Cash Withdraw"
    LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT", "Loan Disbursement"
    INSTALLMENT_PAYMENT = "INSTALLMENT_PAYMENT", "Installment Payment"
    LATE_FEE = "LATE_FEE"
    LOAN_SETTLEMENT = "LOAN_SETTLEMENT"
    REFUND = "REFUND", "Refund"


class TransactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    BLOCKED = "BLOCKED", "Blocked"
    REVERSED = "REVERSED", "Reversed"


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    type = models.CharField(
        max_length=40,
        choices=TransactionType.choices
    )

    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )

    reference_number = models.CharField(
        max_length=32,
        unique=True
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference_number
