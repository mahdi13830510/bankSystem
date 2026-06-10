import jwt
import random

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.users.models import User
from .models import Session, OTPCode

from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.auditlogs.services import AuditLogService
from apps.notifications.services import NotificationService
from apps.notifications.templates import NotificationTemplates


class AuthService:

    # ─────────────────────────────────────────
    #  Login — step 1
    # ─────────────────────────────────────────

    @staticmethod
    def login(phone, password, ip, device):
        user = User.objects.filter(phone=phone).first()

        if not user:
            raise AuthenticationFailed("User not found")

        if user.is_blocked:
            raise AuthenticationFailed("User is blocked")

        if not user.check_password(password):
            user.failed_login_attempts += 1
            user.save(update_fields=["failed_login_attempts"])
            AuditLogService.warning(
                actor=user,
                action="LOGIN_FAILED",
                description="Wrong password",
                ip_address=ip,
            )
            raise AuthenticationFailed("Wrong password")

        # correct password — reset failed attempts
        user.failed_login_attempts = 0
        user.save(update_fields=["failed_login_attempts"])

        # create OTP
        code = str(random.randint(100000, 999999))
        OTPCode.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=2),
        )

        NotificationService.send_template(
            user,
            NotificationTemplates.OTP_SENT,
            code=code,
        )

        if settings.DEBUG:
            print(f"[DEV OTP] phone={user.phone}  code={code}")  # noqa: T201

        AuditLogService.info(
            actor=user,
            action="LOGIN_OTP_SENT",
            ip_address=ip,
        )

        return user

    # ─────────────────────────────────────────
    #  Verify OTP — step 2
    # ─────────────────────────────────────────

    @staticmethod
    def verify_otp(phone, code, ip, device):
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")

        otp = OTPCode.objects.filter(
            user=user,
            code=code,
            is_used=False,
        ).last()

        if not otp:
            AuditLogService.warning(
                actor=user,
                action="OTP_INVALID",
                ip_address=ip,
            )
            raise ValidationError("Invalid OTP")

        if otp.expires_at < timezone.now():
            AuditLogService.warning(
                actor=user,
                action="OTP_EXPIRED",
                ip_address=ip,
            )
            raise ValidationError("OTP expired")

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        AuditLogService.info(
            actor=user,
            action="OTP_VERIFIED",
            ip_address=ip,
        )

        NotificationService.send_template(
            user,
            NotificationTemplates.LOGIN_SUCCESS,
        )

        now = timezone.now()
        access = jwt.encode(
            {
                "user_id": user.id,
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int(
                    (now + timedelta(minutes=getattr(settings, "ACCESS_TOKEN_LIFETIME_MINUTES", 60))).timestamp()),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        refresh = jwt.encode(
            {
                "user_id": user.id,
                "type": "refresh",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=getattr(settings, "REFRESH_TOKEN_LIFETIME_DAYS", 7))).timestamp()),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        Session.objects.create(
            user=user,
            access_token=access,
            refresh_token=refresh,
            device_name=device or "Unknown",
            ip_address=ip,
            expires_at=now + timedelta(
                days=getattr(settings, "REFRESH_TOKEN_LIFETIME_DAYS", 7)
            ),
        )

        return access, refresh

    # ─────────────────────────────────────────
    #  Refresh token
    # ─────────────────────────────────────────

    @staticmethod
    def refresh_token(refresh_token_str):
        try:
            payload = jwt.decode(
                refresh_token_str,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            raise ValidationError("Refresh token expired")
        except jwt.InvalidTokenError:
            raise ValidationError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise ValidationError("Not a refresh token")

        session = Session.objects.filter(
            refresh_token=refresh_token_str,
            status=Session.Status.ACTIVE,
        ).first()

        if not session:
            raise ValidationError("Session not found or already revoked")

        if session.expires_at < timezone.now():
            session.status = Session.Status.EXPIRED
            session.save(update_fields=["status"])
            raise ValidationError("Session expired")

        user = session.user
        now = timezone.now()

        new_access = jwt.encode(
            {
                "user_id": user.id,
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(
                    minutes=getattr(settings, "ACCESS_TOKEN_LIFETIME_MINUTES", 60)
                )).timestamp()),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        session.access_token = new_access
        session.save(update_fields=["access_token"])

        AuditLogService.info(
            actor=user,
            action="TOKEN_REFRESHED",
        )

        return new_access

    # ─────────────────────────────────────────
    #  Logout
    # ─────────────────────────────────────────

    @staticmethod
    def logout(refresh_token_str, actor=None):
        session = Session.objects.filter(
            refresh_token=refresh_token_str
        ).first()

        if session:
            session.status = Session.Status.REVOKED
            session.save(update_fields=["status"])
            AuditLogService.info(
                actor=actor or session.user,
                action="LOGOUT",
            )

    # ─────────────────────────────────────────
    #  Session management
    # ─────────────────────────────────────────

    @staticmethod
    def revoke_session(session, actor=None):
        session.status = Session.Status.REVOKED
        session.save(update_fields=["status"])
        AuditLogService.warning(
            actor=actor,
            action="SESSION_REVOKED",
            metadata={"session_id": session.id},
        )

    @staticmethod
    def revoke_all_sessions(user, exclude_session_id=None, actor=None):
        qs = Session.objects.filter(
            user=user,
            status=Session.Status.ACTIVE,
        )
        if exclude_session_id:
            qs = qs.exclude(id=exclude_session_id)

        count = qs.update(status=Session.Status.REVOKED)

        AuditLogService.warning(
            actor=actor or user,
            action="ALL_SESSIONS_REVOKED",
            metadata={"user_id": user.id, "count": count},
        )
        return count

    @staticmethod
    def expire_stale_sessions():
        now = timezone.now()
        return Session.objects.filter(
            status=Session.Status.ACTIVE,
            expires_at__lt=now,
        ).update(status=Session.Status.EXPIRED)

    # ─────────────────────────────────────────
    #  OTP management
    # ─────────────────────────────────────────

    @staticmethod
    def invalidate_user_otps(user, actor=None):
        """made invalid all the used OTP s of user"""
        count = OTPCode.objects.filter(
            user=user,
            is_used=False,
        ).update(is_used=True)

        AuditLogService.warning(
            actor=actor,
            action="OTPS_INVALIDATED",
            metadata={"user_id": user.id, "count": count},
        )
        return count
