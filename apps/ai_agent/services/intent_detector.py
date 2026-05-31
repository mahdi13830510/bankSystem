from apps.ai_agent.prompts import SYSTEM_PROMPT
from apps.ai_agent.services.llm_service import OllamaService

VALID_INTENTS = {
    "balance",
    "my_accounts",
    "statement",
    "iban_transfer",
    "loan_request",
    "my_loans",
    "my_installments",
    "pay_installment",
    "remaining_debt",
    "notifications",
    "unknown",
}


class IntentDetector:
    @staticmethod
    def detect(message: str) -> dict:
        """Detect intent without conversation context."""
        return IntentDetector.detect_with_context(
            message=message, context=None
        )

    @staticmethod
    def detect_with_context(message: str, context=None) -> dict:
        """
        Detect intent, optionally including recent conversation context
        in the prompt so the model has more information.
        """
        context_block = ""
        if context:
            lines = []
            for msg in context:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
            context_block = (
                    "\nCONVERSATION HISTORY:\n"
                    + "\n".join(lines)
                    + "\n"
            )

        prompt = f"""{SYSTEM_PROMPT}
{context_block}
USER MESSAGE:
{message}

JSON:
"""
        result = OllamaService.generate(prompt)
        return IntentDetector.validate(result)

    @staticmethod
    def validate(data: dict) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Invalid intent format: expected a dict")

        intent = data.get("intent")

        if not intent:
            raise ValueError("Intent missing from response")

        if intent not in VALID_INTENTS:
            raise ValueError(
                f"Unknown intent: '{intent}'. "
                f"Valid intents: {VALID_INTENTS}"
            )

        # Validate required fields per intent
        if intent == "iban_transfer":
            if not data.get("iban"):
                raise ValueError("iban_transfer requires 'iban'")
            if data.get("amount") is None:
                raise ValueError("iban_transfer requires 'amount'")

        if intent == "pay_installment":
            if not data.get("installment_id"):
                raise ValueError("pay_installment requires 'installment_id'")

        if intent == "remaining_debt":
            if not data.get("loan_id"):
                raise ValueError("remaining_debt requires 'loan_id'")
        if intent == "loan_request":

            required = [
                "amount",
                "duration_months",
                "loan_type",
                "monthly_income",
                "existing_debt",
            ]

            for field in required:
                if field not in data:
                    raise ValueError(
                        f"loan_request requires {field}"
                    )

        return data
