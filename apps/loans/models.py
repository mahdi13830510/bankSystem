import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class LoanRequestStatus(models.TextChoices):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LoanStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFAULTED = "DEFAULTED"
    CLOSED = "CLOSED"


class LoanType(models.TextChoices):
    PERSONAL = "PERSONAL"
    HOME = "HOME"
    CAR = "CAR"
    BUSINESS = "BUSINESS"


class LoanRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    duration_months = models.PositiveIntegerField()

    loan_type = models.CharField(max_length=30, choices=LoanType.choices)

    monthly_income = models.DecimalField(max_digits=18, decimal_places=2)
    existing_debt = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    status = models.CharField(
        max_length=30,
        choices=LoanRequestStatus.choices,
        default=LoanRequestStatus.PENDING
    )

    risk_score = models.PositiveIntegerField(default=0)

    manager_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class Loan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    loan_request = models.OneToOneField(
        LoanRequest,
        on_delete=models.PROTECT
    )

    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)

    total_payable = models.DecimalField(max_digits=18, decimal_places=2)
    monthly_installment = models.DecimalField(max_digits=18, decimal_places=2)

    duration_months = models.PositiveIntegerField()

    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.ACTIVE
    )

    started_at = models.DateTimeField(auto_now_add=True)