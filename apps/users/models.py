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


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    address = models.TextField(blank=True, null=True)

    city = models.CharField(max_length=100, blank=True, null=True)

    postal_code = models.CharField(max_length=20, blank=True, null=True)

    birth_date = models.DateField(blank=True, null=True)

    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.fullname


class UserDevice(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="devices"
    )

    device_name = models.CharField(max_length=255)

    ip_address = models.GenericIPAddressField()

    user_agent = models.TextField()

    trusted = models.BooleanField(default=False)

    last_used = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)
