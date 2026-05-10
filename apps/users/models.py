from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        BLOCKED = "blocked", "Blocked"
        SUSPENDED = "suspended", "Suspended"

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        EMPLOYEE = "employee", "Employee"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    id = models.BigAutoField(primary_key=True)

    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)

    fullname = models.CharField(max_length=255)

    national_code = models.CharField(max_length=20, unique=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    primary_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    is_verified = models.BooleanField(default=False)

    failed_login_attempts = models.PositiveIntegerField(default=0)

    blocked_until = models.DateTimeField(null=True, blank=True)

    last_password_change = models.DateTimeField(null=True, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True)

    last_login = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"

    REQUIRED_FIELDS = [
        "email",
        "fullname",
        "national_code"
    ]

    def __str__(self):
        return f"{self.fullname} ({self.phone})"

    @property
    def is_blocked(self):
        if self.blocked_until:
            return self.blocked_until > timezone.now()
        return False