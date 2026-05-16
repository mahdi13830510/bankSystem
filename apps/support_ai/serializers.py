from rest_framework import serializers
from .models import AIConversation, AIMessage


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = [
            "id",
            "conversation",
            "role",
            "content",
            "metadata",
            "created_at"
        ]


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIConversation
        fields = [
            "id",
            "user",
            "created_at",
            "messages"
        ]
