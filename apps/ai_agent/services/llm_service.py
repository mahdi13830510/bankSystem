import json
import re
import requests

from django.conf import settings

from apps.auditlogs.services import AuditLogService


class LLMException(Exception):
    pass


class OllamaService:

    MAX_RETRIES = 3

    @staticmethod
    def generate(prompt: str) -> dict:
        last_error = None

        for attempt in range(OllamaService.MAX_RETRIES):
            try:
                response = requests.post(
                    settings.OLLAMA_URL,
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=settings.OLLAMA_TIMEOUT
                )

                response.raise_for_status()

                data = response.json()
                text = data.get("response", "").strip()

                if not text:
                    raise LLMException("Empty response from model")

                return OllamaService._parse_json(text)

            except LLMException:
                # JSON parse errors — no point retrying
                raise

            except Exception as exc:
                last_error = exc
                AuditLogService.warning(
                    action="AI_AGENT_LLM_RETRY",
                    description=f"Attempt {attempt + 1} failed: {str(exc)}"
                )

        AuditLogService.warning(
            action="AI_AGENT_LLM_ERROR",
            description=str(last_error)
        )

        raise LLMException("LLM service unavailable")

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()

        # Strip markdown code fences
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            return json.loads(text)

        except json.JSONDecodeError:
            AuditLogService.warning(
                action="AI_AGENT_INVALID_JSON",
                description=text[:500]
            )
            raise LLMException("Invalid JSON returned by model")