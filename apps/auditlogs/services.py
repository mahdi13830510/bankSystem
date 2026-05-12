class AuditLogService:

    @staticmethod
    def log(
        *,
        user=None,
        action,
        entity_type,
        entity_id,
        ip=None,
        user_agent=None,
        metadata=None
    ):

        from .models import AuditLog

        return AuditLog.objects.create(
            user_id=getattr(user, "id", None),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            ip_address=ip,
            user_agent=user_agent,
            metadata=metadata or {}
        )