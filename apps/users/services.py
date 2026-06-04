from django.utils import timezone
from .models import User, UserProfile
from apps.auditlogs.services import AuditLogService


class UserService:

    # ─────────────────────────────────────────
    #  Register
    # ─────────────────────────────────────────

    @staticmethod
    def register_user(data, actor=None):
        AuditLogService.info(
            actor=actor,
            action="USER_REGISTERED",
        )
        return User.objects.create_user(**data)

    # ─────────────────────────────────────────
    #  Read
    # ─────────────────────────────────────────

    @staticmethod
    def get_user(user_id):
        return User.objects.get(id=user_id)

    # ─────────────────────────────────────────
    #  Status management
    # ─────────────────────────────────────────

    @staticmethod
    def block_user(user, actor=None, blocked_until=None, reason=""):
        user.status = User.Status.BLOCKED
        if blocked_until:
            user.blocked_until = blocked_until
        user.save(update_fields=["status", "blocked_until"])
        AuditLogService.warning(
            actor=actor,
            action="USER_BLOCKED",
            target_type="User",
            target_id=str(user.id),
            description=reason,
        )

    @staticmethod
    def unblock_user(user, actor=None):
        user.status = User.Status.ACTIVE
        user.blocked_until = None
        user.failed_login_attempts = 0
        user.save(update_fields=["status", "blocked_until", "failed_login_attempts"])
        AuditLogService.info(
            actor=actor,
            action="USER_UNBLOCKED",
            target_type="User",
            target_id=str(user.id),
        )

    @staticmethod
    def suspend_user(user, actor=None, reason=""):
        user.status = User.Status.SUSPENDED
        user.save(update_fields=["status"])
        AuditLogService.warning(
            actor=actor,
            action="USER_SUSPENDED",
            target_type="User",
            target_id=str(user.id),
            description=reason,
        )

    @staticmethod
    def activate_user(user, actor=None):
        user.status = User.Status.ACTIVE
        user.save(update_fields=["status"])
        AuditLogService.info(
            actor=actor,
            action="USER_ACTIVATED",
            target_type="User",
            target_id=str(user.id),
        )

    @staticmethod
    def verify_user(user, actor=None):
        user.is_verified = True
        user.status = User.Status.ACTIVE
        user.save(update_fields=["is_verified", "status"])
        AuditLogService.info(
            actor=actor,
            action="USER_VERIFIED",
            target_type="User",
            target_id=str(user.id),
        )

    # ─────────────────────────────────────────
    #  Role
    # ─────────────────────────────────────────

    @staticmethod
    def change_role(user, new_role, actor=None):
        old_role = user.primary_role
        user.primary_role = new_role

        user.is_staff = new_role in (
            User.Role.EMPLOYEE,
            User.Role.MANAGER,
            User.Role.ADMIN,
        )
        user.save(update_fields=["primary_role", "is_staff"])
        AuditLogService.info(
            actor=actor,
            action="USER_ROLE_CHANGED",
            target_type="User",
            target_id=str(user.id),
            metadata={"old_role": old_role, "new_role": new_role},
        )

    # ─────────────────────────────────────────
    #  Password
    # ─────────────────────────────────────────

    @staticmethod
    def change_password(user, new_password, actor=None):
        user.set_password(new_password)
        user.last_password_change = timezone.now()
        user.save(update_fields=["password", "last_password_change"])
        AuditLogService.info(
            actor=actor or user,
            action="PASSWORD_CHANGED",
            target_type="User",
            target_id=str(user.id),
        )

    # ─────────────────────────────────────────
    #  Failed attempts
    # ─────────────────────────────────────────

    @staticmethod
    def reset_failed_attempts(user, actor=None):
        user.failed_login_attempts = 0
        user.save(update_fields=["failed_login_attempts"])
        AuditLogService.info(
            actor=actor,
            action="FAILED_ATTEMPTS_RESET",
            target_type="User",
            target_id=str(user.id),
        )

    # ─────────────────────────────────────────
    #  Profile
    # ─────────────────────────────────────────

    @staticmethod
    def get_or_create_profile(user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def update_profile(user, data, actor=None):
        profile = UserService.get_or_create_profile(user)
        for field, value in data.items():
            setattr(profile, field, value)
        profile.save()
        AuditLogService.info(
            actor=actor or user,
            action="PROFILE_UPDATED",
            target_type="User",
            target_id=str(user.id),
        )
        return profile