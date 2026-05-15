import uuid
from django.db import models


class AIConversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="ai_conversations"
    )

    created_at = models.DateTimeField(auto_now_add=True)


class AIMessageRole(models.TextChoices):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class AIMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(max_length=20, choices=AIMessageRole.choices)

    content = models.TextField()

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)