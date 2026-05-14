import uuid
from decimal import Decimal
from django.db import models


class InstallmentStatus(models.TextChoices):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    PARTIAL = "PARTIAL"


class Installment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    loan = models.ForeignKey(
        "loans.Loan",
        on_delete=models.CASCADE,
        related_name="installments"
    )

    number = models.PositiveIntegerField()

    due_date = models.DateField()

    amount = models.DecimalField(max_digits=18, decimal_places=2)

    paid_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    penalty_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=InstallmentStatus.choices,
        default=InstallmentStatus.PENDING
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("loan", "number")
        ordering = ["number"]