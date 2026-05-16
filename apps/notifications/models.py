import uuid
from django.db import models


class NotificationChannel(models.TextChoices):
    IN_APP = "IN_APP"
    SMS = "SMS"
    EMAIL = "EMAIL"
    PUSH = "PUSH"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    READ = "READ"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP
    )

    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )

    is_read = models.BooleanField(default=False)

    metadata = models.JSONField(default=dict, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)

    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]
