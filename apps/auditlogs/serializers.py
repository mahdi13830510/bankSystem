from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(
        source="actor.fullname",
        read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "action",
            "target_type",
            "target_id",
            "description",
            "severity",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at"
        ]
