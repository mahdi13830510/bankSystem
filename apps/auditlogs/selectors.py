from .models import AuditLog


class AuditLogSelector:

    @staticmethod
    def recent(limit=50):
        return AuditLog.objects.all()[:limit]

    @staticmethod
    def by_user(user):
        return AuditLog.objects.filter(actor=user)

    @staticmethod
    def by_action(action):
        return AuditLog.objects.filter(action=action)

    @staticmethod
    def critical_logs():
        return AuditLog.objects.filter(
            severity="CRITICAL"
        )