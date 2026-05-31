"""
Tests for apps.ai_agent

Run:
    python manage.py test apps.ai_agent.tests
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.ai_agent.models import (
    AgentConversation,
    AgentMessage,
    PendingAction,
)
from apps.ai_agent.services.intent_detector import IntentDetector
from apps.ai_agent.services.llm_service import LLMException, OllamaService
from apps.ai_agent.services.action_executor import ActionExecutor
from apps.ai_agent.services.conversation_service import ConversationService

User = get_user_model()


# ======================================================================
# Helpers
# ======================================================================

def make_user():
    return User.objects.create_user(
        phone="09120000001",
        password="123456",
        email="test@gmail.com"
    )


def make_conversation(user):
    return AgentConversation.objects.create(user=user)


def make_pending_action(user, intent="iban_transfer", payload=None):
    return PendingAction.objects.create(
        user=user,
        intent=intent,
        payload=payload or {"amount": 100, "iban": "TR123456789"},
        confirmation_text="Transfer 100 TRY to TR123456789",
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )


# ======================================================================
# Model tests
# ======================================================================

class PendingActionModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_is_expired_false_when_not_set(self):
        action = PendingAction.objects.create(
            user=self.user,
            intent="balance",
            payload={},
        )
        self.assertFalse(action.is_expired())

    def test_is_expired_false_when_in_future(self):
        action = make_pending_action(self.user)
        self.assertFalse(action.is_expired())

    def test_is_expired_true_when_past(self):
        action = PendingAction.objects.create(
            user=self.user,
            intent="iban_transfer",
            payload={},
            expires_at=timezone.now() - timezone.timedelta(seconds=1),
        )
        self.assertTrue(action.is_expired())

    def test_str(self):
        action = make_pending_action(self.user)
        self.assertIn("iban_transfer", str(action))
        self.assertIn("PENDING", str(action))


class AgentMessageModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.conv = make_conversation(self.user)

    def test_create_message(self):
        msg = AgentMessage.objects.create(
            conversation=self.conv,
            role=AgentMessage.Role.USER,
            content="سلام",
        )
        self.assertEqual(msg.role, AgentMessage.Role.USER)
        self.assertEqual(msg.content, "سلام")

    def test_messages_ordered_by_created_at(self):
        AgentMessage.objects.create(
            conversation=self.conv, role="user", content="اول"
        )
        AgentMessage.objects.create(
            conversation=self.conv, role="assistant", content="دوم"
        )
        msgs = list(self.conv.messages.all())
        self.assertEqual(msgs[0].content, "اول")
        self.assertEqual(msgs[1].content, "دوم")


# ======================================================================
# IntentDetector tests
# ======================================================================

class IntentDetectorValidateTest(TestCase):

    def test_valid_balance(self):
        data = IntentDetector.validate({"intent": "balance"})
        self.assertEqual(data["intent"], "balance")

    def test_raises_if_not_dict(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate("balance")

    def test_raises_if_intent_missing(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate({})

    def test_raises_if_intent_unknown(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate({"intent": "fly_to_moon"})

    def test_raises_iban_transfer_missing_iban(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate(
                {"intent": "iban_transfer", "amount": 100}
            )

    def test_raises_iban_transfer_missing_amount(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate(
                {"intent": "iban_transfer", "iban": "TR123"}
            )

    def test_raises_pay_installment_missing_id(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate({"intent": "pay_installment"})

    def test_raises_remaining_debt_missing_loan_id(self):
        with self.assertRaises(ValueError):
            IntentDetector.validate({"intent": "remaining_debt"})

    def test_valid_iban_transfer(self):
        data = IntentDetector.validate(
            {"intent": "iban_transfer", "amount": 500, "iban": "TR123"}
        )
        self.assertEqual(data["intent"], "iban_transfer")

    @patch(
        "apps.ai_agent.services.intent_detector.OllamaService.generate"
    )
    def test_detect_calls_generate_and_validate(self, mock_generate):
        mock_generate.return_value = {"intent": "balance"}
        result = IntentDetector.detect("موجودی من چقدره؟")
        self.assertEqual(result["intent"], "balance")
        mock_generate.assert_called_once()

    @patch(
        "apps.ai_agent.services.intent_detector.OllamaService.generate"
    )
    def test_detect_raises_on_invalid_response(self, mock_generate):
        mock_generate.return_value = {"intent": "invalid_xyz"}
        with self.assertRaises(ValueError):
            IntentDetector.detect("...")


# ======================================================================
# OllamaService tests
# ======================================================================

class OllamaServiceParseJsonTest(TestCase):

    def test_clean_json(self):
        result = OllamaService._parse_json('{"intent":"balance"}')
        self.assertEqual(result["intent"], "balance")

    def test_json_with_code_fence(self):
        result = OllamaService._parse_json(
            '```json\n{"intent":"balance"}\n```'
        )
        self.assertEqual(result["intent"], "balance")

    def test_json_with_plain_fence(self):
        result = OllamaService._parse_json('```{"intent":"balance"}```')
        self.assertEqual(result["intent"], "balance")

    def test_invalid_json_raises_llm_exception(self):
        with self.assertRaises(LLMException):
            OllamaService._parse_json("not json at all")

    @patch("apps.ai_agent.services.llm_service.requests.post")
    def test_generate_returns_parsed_dict(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "response": '{"intent":"balance"}'
        }
        result = OllamaService.generate("test prompt")
        self.assertEqual(result["intent"], "balance")

    @patch("apps.ai_agent.services.llm_service.requests.post")
    def test_generate_retries_on_connection_error(self, mock_post):
        mock_post.side_effect = ConnectionError("timeout")
        with self.assertRaises(LLMException):
            OllamaService.generate("test prompt")
        self.assertEqual(mock_post.call_count, OllamaService.MAX_RETRIES)

    @patch("apps.ai_agent.services.llm_service.requests.post")
    def test_generate_raises_on_empty_response(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"response": ""}
        with self.assertRaises(LLMException):
            OllamaService.generate("test prompt")


# ======================================================================
# ActionExecutor tests
# ======================================================================

class ActionExecutorCreateActionsTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_create_iban_transfer_creates_pending_action(self):
        result = ActionExecutor.create_iban_transfer(
            user=self.user, amount=500, iban="TR123456789"
        )
        self.assertTrue(result["needs_confirmation"])
        action = PendingAction.objects.get(id=result["action_id"])
        self.assertEqual(action.intent, "iban_transfer")
        self.assertEqual(action.status, PendingAction.Status.PENDING)
        self.assertEqual(action.payload["amount"], 500)

    def test_create_loan_request_creates_pending_action(self):
        payload = {
            "intent": "loan_request",
            "amount": 10000,
            "duration_months": 12,
        }
        result = ActionExecutor.create_loan_request(
            user=self.user, payload=payload
        )
        self.assertTrue(result["needs_confirmation"])
        action = PendingAction.objects.get(id=result["action_id"])
        self.assertEqual(action.intent, "loan_request")

    def test_create_installment_payment_creates_pending_action(self):
        inst_id = "123e4567-e89b-12d3-a456-426614174000"
        result = ActionExecutor.create_installment_payment(
            user=self.user, installment_id=inst_id
        )
        self.assertTrue(result["needs_confirmation"])
        action = PendingAction.objects.get(id=result["action_id"])
        self.assertEqual(action.payload["installment_id"], inst_id)

    def test_execute_action_raises_on_expired(self):
        action = PendingAction.objects.create(
            user=self.user,
            intent="iban_transfer",
            payload={"amount": 100, "iban": "TR1"},
            expires_at=timezone.now() - timezone.timedelta(seconds=1),
        )
        with self.assertRaises(ValueError, msg="Action has expired"):
            ActionExecutor.execute_action(action, "127.0.0.1")

    def test_execute_action_raises_on_unsupported_intent(self):
        action = PendingAction.objects.create(
            user=self.user,
            intent="fly_to_moon",
            payload={},
        )
        with self.assertRaises(ValueError):
            ActionExecutor.execute_action(action, "127.0.0.1")

    @patch(
        "apps.ai_agent.services.action_executor.AccountService"
        ".get_primary_account"
    )
    @patch("apps.ai_agent.services.action_executor.Account.objects.get")
    @patch(
        "apps.ai_agent.services.action_executor.TransactionService"
        ".iban_transfer"
    )
    @patch("apps.ai_agent.services.action_executor.AuditLogService.info")
    def test_execute_iban_transfer_marks_executed(
        self, mock_audit, mock_transfer, mock_account_get, mock_primary
    ):
        mock_txn = MagicMock()
        mock_txn.id = "txn-uuid-001"
        mock_transfer.return_value = mock_txn

        action = make_pending_action(self.user)
        result = ActionExecutor.execute_action(action, "127.0.0.1")

        action.refresh_from_db()
        self.assertTrue(result["success"])
        self.assertEqual(action.status, PendingAction.Status.EXECUTED)
        self.assertIsNotNone(action.executed_at)
        mock_audit.assert_called_once()


# ======================================================================
# ConversationService tests
# ======================================================================

class ConversationServiceTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.conv = make_conversation(self.user)

    # -- save_message --

    def test_save_message_user(self):
        msg = ConversationService.save_message(
            conversation=self.conv,
            role=AgentMessage.Role.USER,
            text="سلام",
        )
        self.assertEqual(msg.content, "سلام")
        self.assertEqual(msg.role, AgentMessage.Role.USER)

    def test_save_message_assistant(self):
        msg = ConversationService.save_message(
            conversation=self.conv,
            role=AgentMessage.Role.ASSISTANT,
            text="موجودی شما ۱۰۰ لیر است",
        )
        self.assertEqual(msg.role, AgentMessage.Role.ASSISTANT)

    # -- get_pending_action --

    def test_get_pending_action_returns_latest(self):
        # Force a1 to have an older created_at so ordering is deterministic
        now = timezone.now()
        a1 = PendingAction.objects.create(
            user=self.user,
            intent="iban_transfer",
            payload={"amount": 100, "iban": "TR1"},
            expires_at=now + timezone.timedelta(minutes=5),
        )
        PendingAction.objects.filter(pk=a1.pk).update(
            created_at=now - timezone.timedelta(seconds=10)
        )
        a2 = PendingAction.objects.create(
            user=self.user,
            intent="iban_transfer",
            payload={"amount": 200, "iban": "TR2"},
            expires_at=now + timezone.timedelta(minutes=5),
        )
        result = ConversationService.get_pending_action(self.user)
        self.assertEqual(result.id, a2.id)

    def test_get_pending_action_ignores_executed(self):
        action = make_pending_action(self.user)
        action.status = PendingAction.Status.EXECUTED
        action.save()
        result = ConversationService.get_pending_action(self.user)
        self.assertIsNone(result)

    def test_get_pending_action_expires_stale(self):
        PendingAction.objects.create(
            user=self.user,
            intent="balance",
            payload={},
            expires_at=timezone.now() - timezone.timedelta(seconds=1),
        )
        result = ConversationService.get_pending_action(self.user)
        self.assertIsNone(result)

    # -- is_confirmation / is_cancel --

    def test_is_confirmation_true(self):
        for word in ["بله", "yes", "ok", "confirm", "تایید"]:
            self.assertTrue(
                ConversationService.is_confirmation(word),
                f"Expected '{word}' to be confirmation"
            )

    def test_is_confirmation_false(self):
        self.assertFalse(ConversationService.is_confirmation("نه"))
        self.assertFalse(ConversationService.is_confirmation("شاید"))

    def test_is_cancel_true(self):
        for word in ["لغو", "نه", "cancel", "no"]:
            self.assertTrue(
                ConversationService.is_cancel(word),
                f"Expected '{word}' to be cancel"
            )

    def test_is_cancel_false(self):
        self.assertFalse(ConversationService.is_cancel("بله"))

    # -- cancel_pending_action --

    def test_cancel_pending_action(self):
        action = make_pending_action(self.user)
        result = ConversationService.cancel_pending_action(action)
        action.refresh_from_db()
        self.assertEqual(action.status, PendingAction.Status.CANCELLED)
        self.assertFalse(result["success"])

    # -- process_confirmation --

    def test_process_confirmation_returns_none_without_pending(self):
        result = ConversationService.process_confirmation(
            user=self.user,
            conversation=self.conv,
            text="بله",
            ip_address="127.0.0.1",
        )
        self.assertIsNone(result)

    def test_process_confirmation_cancels_on_no(self):
        make_pending_action(self.user)
        result = ConversationService.process_confirmation(
            user=self.user,
            conversation=self.conv,
            text="لغو",
            ip_address="127.0.0.1",
        )
        self.assertFalse(result["success"])
        self.assertIn("لغو", result["message"])

    def test_process_confirmation_asks_for_clarification(self):
        make_pending_action(self.user)
        result = ConversationService.process_confirmation(
            user=self.user,
            conversation=self.conv,
            text="شاید",
            ip_address="127.0.0.1",
        )
        self.assertFalse(result["success"])

    # -- build_context --

    def test_build_context_ordering(self):
        now = timezone.now()
        for i in range(3):
            msg = AgentMessage.objects.create(
                conversation=self.conv,
                role=AgentMessage.Role.USER,
                content=f"msg {i}",
            )
            # Ensure strictly increasing created_at for deterministic order
            AgentMessage.objects.filter(pk=msg.pk).update(
                created_at=now + timezone.timedelta(seconds=i)
            )
        ctx = ConversationService.build_context(self.conv)
        self.assertEqual(len(ctx), 3)
        self.assertEqual(ctx[0]["content"], "msg 0")
        self.assertEqual(ctx[2]["content"], "msg 2")

    def test_build_context_max_10(self):
        for i in range(15):
            AgentMessage.objects.create(
                conversation=self.conv,
                role=AgentMessage.Role.USER,
                content=f"msg {i}",
            )
        ctx = ConversationService.build_context(self.conv)
        self.assertEqual(len(ctx), 10)

    # -- process_message --

    @patch(
        "apps.ai_agent.services.conversation_service"
        ".IntentDetector.detect_with_context"
    )
    @patch(
        "apps.ai_agent.services.conversation_service"
        ".ActionExecutor.balance"
    )
    def test_process_message_balance_intent(
        self, mock_balance, mock_detect
    ):
        mock_detect.return_value = {"intent": "balance"}
        mock_balance.return_value = {
            "type": "balance",
            "balance": "5000",
            "currency": "TRY",
            "account_number": "ACC001",
            "iban": "TR001",
            "status": "ACTIVE",
        }

        result = ConversationService.process_message(
            user=self.user,
            text="موجودی من",
            ip_address="127.0.0.1",
        )

        self.assertEqual(result["type"], "balance")
        mock_balance.assert_called_once_with(self.user)

        # Assistant message should be saved
        msgs = AgentMessage.objects.filter(
            conversation__user=self.user,
            role=AgentMessage.Role.ASSISTANT,
        )
        self.assertTrue(msgs.exists())

    @patch(
        "apps.ai_agent.services.conversation_service"
        ".IntentDetector.detect_with_context"
    )
    def test_process_message_unknown_intent(self, mock_detect):
        mock_detect.return_value = {"intent": "unknown"}

        result = ConversationService.process_message(
            user=self.user,
            text="بلبل بز",
            ip_address="127.0.0.1",
        )

        self.assertEqual(result["type"], "unknown")

    @patch(
        "apps.ai_agent.services.conversation_service"
        ".IntentDetector.detect_with_context"
    )
    def test_process_message_llm_error_returns_error_type(
        self, mock_detect
    ):
        mock_detect.side_effect = LLMException("unavailable")

        result = ConversationService.process_message(
            user=self.user,
            text="هر چیزی",
            ip_address="127.0.0.1",
        )

        self.assertEqual(result["type"], "error")

    @patch(
        "apps.ai_agent.services.conversation_service"
        ".IntentDetector.detect_with_context"
    )
    def test_process_message_iban_transfer_creates_pending(
        self, mock_detect
    ):
        mock_detect.return_value = {
            "intent": "iban_transfer",
            "amount": 200,
            "iban": "TR999",
        }

        result = ConversationService.process_message(
            user=self.user,
            text="200 لیر به TR999 بفرست",
            ip_address="127.0.0.1",
        )

        self.assertTrue(result["needs_confirmation"])
        self.assertTrue(
            PendingAction.objects.filter(
                user=self.user, intent="iban_transfer"
            ).exists()
        )

    @patch(
        "apps.ai_agent.services.conversation_service"
        ".ActionExecutor.execute_action"
    )
    def test_process_message_confirm_executes_action(
        self, mock_execute
    ):
        make_pending_action(self.user)
        mock_execute.return_value = {
            "success": True, "transaction_id": "t1"
        }

        result = ConversationService.process_message(
            user=self.user,
            text="بله",
            ip_address="127.0.0.1",
        )

        self.assertTrue(result["success"])
        mock_execute.assert_called_once()

    def test_process_message_saves_user_message(self):
        with patch(
            "apps.ai_agent.services.conversation_service"
            ".IntentDetector.detect_with_context",
            return_value={"intent": "unknown"},
        ):
            ConversationService.process_message(
                user=self.user,
                text="سلام",
                ip_address="127.0.0.1",
            )

        user_msgs = AgentMessage.objects.filter(
            conversation__user=self.user,
            role=AgentMessage.Role.USER,
        )
        self.assertTrue(user_msgs.filter(content="سلام").exists())

    def test_process_message_uses_existing_conversation(self):
        existing = make_conversation(self.user)
        count_before = AgentConversation.objects.filter(user=self.user).count()

        with patch(
            "apps.ai_agent.services.conversation_service"
            ".IntentDetector.detect_with_context",
            return_value={"intent": "unknown"},
        ):
            ConversationService.process_message(
                user=self.user,
                text="سلام",
                ip_address="127.0.0.1",
                conversation_id=existing.id,
            )

        # Message saved under the existing conversation
        self.assertTrue(
            AgentMessage.objects.filter(
                conversation=existing
            ).exists()
        )
        # No new conversation was created
        count_after = AgentConversation.objects.filter(user=self.user).count()
        self.assertEqual(count_before, count_after)