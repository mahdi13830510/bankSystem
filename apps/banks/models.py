import uuid
from django.db import models


class BankStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    SUSPENDED = "SUSPENDED"


class Bank(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=120, unique=True)

    code = models.CharField(max_length=10, unique=True)

    iban_prefix = models.CharField(max_length=5, default="TR")

    swift_code = models.CharField(max_length=20, unique=True)

    transfer_fee = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=BankStatus.choices,
        default=BankStatus.ACTIVE
    )

    supports_instant_transfer = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "banks"


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        related_name="branches"
    )

    name = models.CharField(max_length=120)

    code = models.CharField(max_length=20)

    city = models.CharField(max_length=100)

    address = models.TextField()

    phone = models.CharField(max_length=30, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "bank_branches"
        unique_together = ("bank", "code")
