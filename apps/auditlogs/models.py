import uuid
from django.db import models


class AuditActionType(models.TextChoices):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    TRANSACTION = "TRANSACTION"
    FRAUD_DECISION = "FRAUD_DECISION"
    LOAN = "LOAN"
    ACCOUNT = "ACCOUNT"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField(null=True, blank=True)

    action = models.CharField(max_length=30, choices=AuditActionType.choices)

    entity_type = models.CharField(max_length=50)   # e.g. Transaction, Account

    entity_id = models.CharField(max_length=100)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    user_agent = models.TextField(blank=True, null=True)

    metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]