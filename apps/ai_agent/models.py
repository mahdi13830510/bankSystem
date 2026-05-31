from django.db import models
from django.conf import settings
from django.utils import timezone


class AgentConversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations"
    )

    title = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "ai_conversations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conversation #{self.id} - {self.user}"


class AgentMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    conversation = models.ForeignKey(
        AgentConversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "ai_messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class PendingAction(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        EXECUTED = "EXECUTED"
        CANCELLED = "CANCELLED"
        EXPIRED = "EXPIRED"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_ai_actions"
    )

    intent = models.CharField(
        max_length=100
    )

    payload = models.JSONField(
        default=dict
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    confirmation_text = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    executed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = "ai_pending_actions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.intent} - {self.status}"

    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False


class ConversationMemory(models.Model):
    conversation = models.OneToOneField(
        AgentConversation,
        on_delete=models.CASCADE,
        related_name="memory"
    )

    context = models.JSONField(
        default=dict
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "ai_conversation_memory"

    def __str__(self):
        return f"Memory for {self.conversation}"