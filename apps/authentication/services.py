import jwt
import random

from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from .models import Session, OTPCode

from rest_framework.exceptions import AuthenticationFailed, ValidationError

from ..auditlogs.services import AuditLogService
from ..notifications.services import NotificationService
from ..notifications.templates import NotificationTemplates


class AuthService:

    @staticmethod
    def login(phone, password, ip, device):

        user = User.objects.filter(phone=phone).first()

        if not user:
            raise Exception("User not found")

        if user.is_blocked:
            raise Exception("User blocked")

        if not user.check_password(password):
            user.failed_login_attempts += 1
            user.save()
            AuditLogService.log(
                user=None,
                action="LOGIN",
                entity_type="AUTH",
                entity_id=user.phone,
                metadata={"status": "FAILED"}
            )
            raise AuthenticationFailed("Wrong password")
        user.failed_login_attempts = 0
        user.save()
        AuditLogService.log(
            user=user,
            action="LOGIN",
            entity_type="Session",
            entity_id=user.session.id,
            metadata={"status": "SUCCESS"}
        )
        NotificationService.send_template(
            user,
            NotificationTemplates.LOGIN_SUCCESS
        )

        code = str(random.randint(100000, 999999))

        OTPCode.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=2)
        )

        return user

    @staticmethod
    def verify_otp(phone, code, ip, device):

        user = User.objects.get(phone=phone)

        otp = OTPCode.objects.filter(
            user=user,
            code=code,
            is_used=False
        ).last()
        NotificationService.send_template(
            user,
            NotificationTemplates.OTP_SENT,
            code=otp
        )
        if not otp:
            AuditLogService.log(
                user=user,
                action="LOGIN",
                entity_type="OTP",
                entity_id=user.session.id,
                metadata={"otp_verified": False}
            )
            raise ValidationError("Invalid OTP")

        if otp.expires_at < timezone.now():
            AuditLogService.log(
                user=user,
                action="LOGIN",
                entity_type="OTP",
                entity_id=user.session.id,
                metadata={"otp_verified": False}
            )
            raise Exception("OTP expired")

        otp.is_used = True
        otp.save()
        AuditLogService.log(
            user=user,
            action="LOGIN",
            entity_type="OTP",
            entity_id=user.session.id,
            metadata={"otp_verified": True}
        )

        access = jwt.encode(
            {"user_id": user.id},
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        refresh = jwt.encode(
            {"user_id": user.id, "type": "refresh"},
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        Session.objects.create(
            user=user,
            access_token=access,
            refresh_token=refresh,
            device_name=device,
            ip_address=ip,
            expires_at=timezone.now() + timedelta(days=7)
        )

        return access, refresh

    @staticmethod
    def logout(refresh_token):

        session = Session.objects.filter(
            refresh_token=refresh_token
        ).first()

        if session:
            session.status = "revoked"
            session.save()