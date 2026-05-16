import uuid

from django.db import models


class AuditSeverity(models.TextChoices):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,
                          editable=False)

    actor = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs"
    )

    action = models.CharField(max_length=100)

    target_type = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    target_id = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    description = models.TextField(blank=True, default="")

    severity = models.CharField(
        max_length=20,
        choices=AuditSeverity.choices,
        default=AuditSeverity.INFO
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField(blank=True, default="")

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["severity"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.created_at}"