from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.conf import settings


def get_default_session_expiry():
    minutes = getattr(settings, 'SESSION_EXPIRATION_MINUTES', 10)
    return timezone.now() + timedelta(minutes=minutes)


class Session(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    access_token = models.TextField()

    refresh_token = models.TextField()

    device_name = models.CharField(max_length=255,default="Unknown")

    ip_address = models.GenericIPAddressField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(default=get_default_session_expiry)

    last_used = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.phone} - {self.device_name}"


def get_expiry_time():
    return timezone.now() + timedelta(minutes=2)


class OTPCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    code = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(default=get_expiry_time)

    is_used = models.BooleanField(default=False)
