from django.contrib import admin

from .models import (
    AgentConversation,
    AgentMessage,
    PendingAction,
    ConversationMemory
)


admin.site.register(AgentConversation)
admin.site.register(AgentMessage)
admin.site.register(PendingAction)
admin.site.register(ConversationMemory)