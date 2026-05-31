from django.utils import timezone

from apps.ai_agent.models import (
    AgentConversation,
    AgentMessage,
    PendingAction,
)
from apps.ai_agent.services.llm_service import OllamaService, LLMException
from apps.ai_agent.services.intent_detector import IntentDetector
from apps.ai_agent.services.action_executor import ActionExecutor
from apps.ai_agent.prompts import SYSTEM_PROMPT
from apps.auditlogs.services import AuditLogService


class ConversationService:

    # ------------------------------------------------------------------ #
    #  Conversation / message helpers                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_or_create_conversation(user, conversation_id=None):
        if conversation_id:
            return AgentConversation.objects.get(
                id=conversation_id, user=user
            )
        return AgentConversation.objects.create(user=user)

    @staticmethod
    def save_message(*, conversation, role, text):
        return AgentMessage.objects.create(
            conversation=conversation,
            role=role,
            content=text,
        )

    # ------------------------------------------------------------------ #
    #  Pending-action helpers                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_pending_action(user):
        action = (
            PendingAction.objects
            .filter(user=user, status=PendingAction.Status.PENDING)
            .order_by("-created_at")
            .first()
        )

        if action and action.is_expired():
            action.status = PendingAction.Status.EXPIRED
            action.save(update_fields=["status"])
            return None

        return action

    @staticmethod
    def is_confirmation(text):
        return text.lower().strip() in {
            "بله", "آره", "انجام بده", "تایید",
            "اوکی", "ok", "yes", "confirm",
        }

    @staticmethod
    def is_cancel(text):
        return text.lower().strip() in {
            "لغو", "نه", "کنسل", "cancel", "no",
        }

    @staticmethod
    def cancel_pending_action(action):
        action.status = PendingAction.Status.CANCELLED
        action.save(update_fields=["status"])
        return {"success": False, "message": "عملیات لغو شد."}

    @staticmethod
    def process_confirmation(*, user, conversation, text, ip_address):
        action = ConversationService.get_pending_action(user)

        if not action:
            return None

        if ConversationService.is_cancel(text):
            result = ConversationService.cancel_pending_action(action)
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text=result["message"],
            )
            return result

        if ConversationService.is_confirmation(text):
            try:
                result = ActionExecutor.execute_action(action, ip_address)
                ConversationService.save_message(
                    conversation=conversation,
                    role=AgentMessage.Role.ASSISTANT,
                    text="عملیات با موفقیت انجام شد.",
                )
                return result
            except Exception as e:
                return {
                    "success": False,
                    "message": str(e)
                }


        return {"success": False, "message": "لطفا تایید یا لغو کنید."}

    # ------------------------------------------------------------------ #
    #  Context builder                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_context(conversation):
        messages = (
            AgentMessage.objects
            .filter(conversation=conversation)
            .order_by("-created_at")[:10]
        )

        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(list(messages))
        ]

    # ------------------------------------------------------------------ #
    #  Main entry point                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def process_message(*, user, text, ip_address, conversation_id=None):
        conversation = ConversationService.get_or_create_conversation(
            user, conversation_id
        )

        ConversationService.save_message(
            conversation=conversation,
            role=AgentMessage.Role.USER,
            text=text,
        )

        # Check if user is confirming / cancelling a pending action
        confirmation = ConversationService.process_confirmation(
            user=user,
            conversation=conversation,
            text=text,
            ip_address=ip_address,
        )
        if confirmation:
            return confirmation

        # Build context and call LLM
        context = ConversationService.build_context(conversation)

        try:
            intent_data = IntentDetector.detect_with_context(
                message=text, context=context
            )
        except LLMException as exc:
            AuditLogService.warning(
                action="AI_AGENT_LLM_ERROR",
                description=str(exc)
            )
            reply = "متأسفیم، در حال حاضر سرویس هوش مصنوعی در دسترس نیست."
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text=reply,
            )
            return {"type": "error", "message": reply}

        intent = intent_data.get("intent")

        # ---- Read-only intents ----------------------------------------

        if intent == "balance":
            result = ActionExecutor.balance(user)
            reply = f"موجودی شما {result['balance']} {result['currency']}"
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text=reply,
            )
            return result

        if intent == "my_accounts":
            result = ActionExecutor.my_accounts(user)
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text="لیست حساب‌های شما:",
            )
            return result

        if intent == "statement":
            result = ActionExecutor.statement(user)
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text="صورت‌حساب اخیر شما:",
            )
            return result

        if intent == "my_loans":
            result = ActionExecutor.my_loans(user)
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text="وام‌های شما:",
            )
            return result

        if intent == "my_installments":
            result = ActionExecutor.my_installments(user)
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text="اقساط شما:",
            )
            return result

        if intent == "remaining_debt":
            result = ActionExecutor.remaining_debt(
                user, intent_data["loan_id"]
            )
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text=f"باقیمانده بدهی: {result['remaining_debt']}",
            )
            return result

        if intent == "notifications":
            result = ActionExecutor.notifications(user)
            ConversationService.save_message(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                text="اعلان‌های شما:",
            )
            return result

        # ---- Write intents (require confirmation) ----------------------

        if intent == "iban_transfer":
            return ActionExecutor.create_iban_transfer(
                user=user,
                amount=intent_data["amount"],
                iban=intent_data["iban"],
            )

        if intent == "loan_request":
            return ActionExecutor.create_loan_request(
                user=user, payload=intent_data
            )

        if intent == "pay_installment":
            return ActionExecutor.create_installment_payment(
                user=user,
                installment_id=intent_data["installment_id"],
            )

        # ---- Fallback --------------------------------------------------

        reply = "متأسفیم، درخواست شما را متوجه نشدم. لطفا واضح‌تر بیان کنید."
        ConversationService.save_message(
            conversation=conversation,
            role=AgentMessage.Role.ASSISTANT,
            text=reply,
        )
        AuditLogService.info(actor=user, action="AI_AGENT_UNKNOWN_INTENT")
        return {"type": "unknown", "message": reply}