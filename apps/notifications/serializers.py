from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "title",
            "message",
            "channel",
            "status",
            "is_read",
            "metadata",
            "sent_at",
            "read_at",
            "created_at",

        ]
        read_only_fields = ("user",)
