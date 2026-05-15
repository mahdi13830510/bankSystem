from .models import AuditLog, AuditSeverity


class AuditLogService:

    @staticmethod
    def log(
        actor=None,
        action="UNKNOWN",
        target_type="",
        target_id="",
        description="",
        severity="INFO",
        ip_address=None,
        user_agent="",
        metadata=None
    ):
        return AuditLog.objects.create(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )

    @staticmethod
    def info(**kwargs):
        kwargs["severity"] = AuditSeverity.INFO
        return AuditLogService.log(**kwargs)

    @staticmethod
    def warning(**kwargs):
        kwargs["severity"] = AuditSeverity.WARNING
        return AuditLogService.log(**kwargs)

    @staticmethod
    def critical(**kwargs):
        kwargs["severity"] = AuditSeverity.CRITICAL
        return AuditLogService.log(**kwargs)