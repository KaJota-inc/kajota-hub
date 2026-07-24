import json
import os
from typing import Any

from payflow.kb import KB
from payflow.models import Envelope, TriageResult
from payflow.triage.llm import _payload_to_result
from payflow.triage.prompt import TRIAGE_TOOL, build_system_prompt, build_user_message

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

# Same fields as Anthropic's TRIAGE_TOOL input_schema — Gemini's response_schema
# just consumes a JSON Schema directly.
TRIAGE_RESPONSE_SCHEMA = TRIAGE_TOOL["input_schema"]


class GeminiTriager:
    """Gemini-backed triager. Satisfies the same TriagerProtocol as LLMTriager.

    MVP notes:
    - Uses response_schema for structured output (Gemini's forced-JSON mode).
    - No prompt caching yet — send the full system prompt every call. That inflates
      input tokens by ~1800 vs the cached Anthropic path but Flash-Lite is cheap
      enough per token that it's still ~5x cheaper end-to-end.
    - When Gemini caching lands here, revisit `bench.py` token profiles.
    """

    def __init__(
        self,
        client: Any = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ):
        self.client = client or _default_client()
        self.model = model or os.environ.get("PAYFLOW_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.max_tokens = max_tokens

    def triage(self, env: Envelope, kb: KB) -> TriageResult:
        # Anthropic's system prompt is a list of typed blocks (for cache_control);
        # Gemini's system_instruction is a plain string. Concatenate the text parts.
        system_blocks = build_system_prompt(kb)
        system_text = "\n\n".join(b["text"] for b in system_blocks)
        user_text = build_user_message(env)

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_text,
            config={
                "system_instruction": system_text,
                "response_mime_type": "application/json",
                "response_schema": TRIAGE_RESPONSE_SCHEMA,
                "max_output_tokens": self.max_tokens,
            },
        )
        payload = _extract_payload(response)
        return _payload_to_result(env, payload)


def _default_client() -> Any:
    """Lazy import so pytest doesn't need google-genai if using a fake client."""
    try:
        from google import genai
    except ImportError as e:
        raise ImportError(
            "google-genai required for Gemini triager. Install with: uv sync --extra gemini"
        ) from e
    # Picks up GEMINI_API_KEY or GOOGLE_API_KEY from env.
    return genai.Client()


def _extract_payload(response: Any) -> dict:
    """Gemini's response with response_mime_type='application/json' puts JSON in .text."""
    text = getattr(response, "text", None)
    if text is None:
        raise RuntimeError(f"Gemini returned no text. Response: {response!r}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini JSON parse failed: {e}. Text: {text!r}") from e
