from rest_framework import serializers
from .models import AgentConversation, AgentMessage, PendingAction


# ─────────────────────────────────────────
#  Chat
# ─────────────────────────────────────────

class ChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=5000)
    conversation_id = serializers.IntegerField(required=False)


# ─────────────────────────────────────────
#  Messages
# ─────────────────────────────────────────

class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage
        fields = ["id", "role", "content", "created_at"]


# ─────────────────────────────────────────
#  Conversations
# ─────────────────────────────────────────

class ConversationListSerializer(serializers.ModelSerializer):
    """conversation list without detail"""
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = AgentConversation
        fields = ["id", "title", "created_at", "updated_at", "last_message"]

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if msg:
            return {
                "role": msg.role,
                "content": msg.content[:100],
                "created_at": msg.created_at,
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """conversation list with detail"""
    messages = AgentMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AgentConversation
        fields = ["id", "title", "created_at", "updated_at", "messages"]


class AdminConversationSerializer(serializers.ModelSerializer):
    """for admin — with user detail"""
    messages = AgentMessageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source="user.fullname", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = AgentConversation
        fields = [
            "id", "user", "user_name", "user_phone",
            "title", "created_at", "updated_at", "messages",
        ]


# ─────────────────────────────────────────
#  Pending Actions
# ─────────────────────────────────────────

class PendingActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingAction
        fields = [
            "id", "intent", "payload", "status",
            "confirmation_text", "created_at", "executed_at", "expires_at",
        ]


class AdminPendingActionSerializer(serializers.ModelSerializer):
    """for admin — with user detail"""
    user_name = serializers.CharField(source="user.fullname", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = PendingAction
        fields = [
            "id", "user", "user_name", "user_phone",
            "intent", "payload", "status",
            "confirmation_text", "created_at", "executed_at", "expires_at",
        ]


# ─────────────────────────────────────────
#  Filters (Admin)
# ─────────────────────────────────────────

class AdminConversationFilterSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(
        required=False,
        help_text="search in messages",
    )


class AdminPendingActionFilterSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    intent = serializers.CharField(required=False)
    status = serializers.ChoiceField(
        choices=PendingAction.Status.choices, required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
