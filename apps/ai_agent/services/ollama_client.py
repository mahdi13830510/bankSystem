import requests
import json


class OllamaClient:

    BASE_URL = "http://localhost:11434/api/chat"
    MODEL = "llama3.1"

    @staticmethod
    def chat(message, context=None):

        system_prompt = """
You are a banking intent detection system.

You MUST return ONLY valid JSON.
No explanation. No text. No markdown.

Available intents:
- check_balance
- my_accounts
- statement
- iban_transfer
- card_transfer
- loan_request
- my_loans
- my_installments
- pay_installment
- remaining_debt
- general_chat

Rules:
- If user wants money transfer → iban_transfer
- If user asks balance → check_balance
- If unclear → general_chat

For transfer intents you MUST include:
- amount (if exists)
- iban (if exists)

Output format MUST be:
{
  "intent": "...",
  "amount": "...",
  "iban": "...",
  "installment_id": "...",
  "loan_id": "..."
}
"""

        payload = {
            "model": OllamaClient.MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                *(
                    context or []
                ),
                {"role": "user", "content": message}
            ],
            "stream": False
        }

        response = requests.post(
            OllamaClient.BASE_URL,
            json=payload
        )

        data = response.json()

        return data["message"]["content"]