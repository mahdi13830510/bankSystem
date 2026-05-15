from .models import AIConversation, AIMessage, AIMessageRole
from .llm import SimpleLLM
from .prompts import BANK_SYSTEM_PROMPT


class AIService:

    @staticmethod
    def get_or_create_conversation(user):

        conv = AIConversation.objects.filter(user=user).first()

        if not conv:
            conv = AIConversation.objects.create(user=user)

        return conv

    @staticmethod
    def send_message(user, message_text):

        conv = AIService.get_or_create_conversation(user)

        AIMessage.objects.create(
            conversation=conv,
            role=AIMessageRole.USER,
            content=message_text
        )

        response = SimpleLLM.generate_response(
            BANK_SYSTEM_PROMPT,
            message_text
        )

        AIMessage.objects.create(
            conversation=conv,
            role=AIMessageRole.ASSISTANT,
            content=response
        )

        return response