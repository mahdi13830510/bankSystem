from .models import User
from ..auditlogs.services import AuditLogService


class UserService:

    @staticmethod
    def register_user(data):
        AuditLogService.log(
            user="admin",
            action="ADMIN",
            entity_type="User",
            entity_id=data.user.id,
            metadata={"change": "USER REGISTRATION"}
        )
        return User.objects.create_user(**data)

    @staticmethod
    def get_user(user_id):
        return User.objects.get(id=user_id)

    @staticmethod
    def block_user(user):
        user.status = "blocked"
        user.save()
        AuditLogService.log(
            user="Admin",
            action="ADMIN",
            entity_type="User",
            entity_id=user.id,
            metadata={"change": "USER_BLOCKED"}
        )

    @staticmethod
    def verify_user(user):
        user.is_verified = True
        user.status = "active"
        user.save()

    @staticmethod
    def change_password(user, new_password):
        user.set_password(new_password)
        user.save()
        AuditLogService.log(
            user=user,
            action="ADMIN",
            entity_type="User",
            entity_id=user.id,
            metadata={"change": "PASSWORD_CHANGE"}
        )
