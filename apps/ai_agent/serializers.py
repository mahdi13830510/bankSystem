from rest_framework import serializers

from .models import (
    AgentConversation,
    AgentMessage,
    PendingAction
)


class ChatSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=5000
    )

    conversation_id = serializers.IntegerField(
        required=False
    )


class ConfirmActionSerializer(serializers.Serializer):
    action_id = serializers.IntegerField()


class CancelActionSerializer(serializers.Serializer):
    action_id = serializers.IntegerField()


class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage

        fields = [
            "id",
            "role",
            "content",
            "created_at"
        ]


class ConversationSerializer(serializers.ModelSerializer):
    messages = AgentMessageSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = AgentConversation

        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "messages"
        ]


class PendingActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingAction

        fields = [
            "id",
            "intent",
            "payload",
            "status",
            "confirmation_text",
            "created_at",
            "executed_at"
        ]
