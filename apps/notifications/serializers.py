from rest_framework import serializers
from .models import Notification, NotificationChannel


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


class SendNotificationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP
    )
    metadata = serializers.DictField(required=False, default=dict)


class BroadcastSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
