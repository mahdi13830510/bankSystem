from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(
        source="actor.fullname",
        read_only=True
    )

    class Meta:
        model = AuditLog
        fields = "__all__"