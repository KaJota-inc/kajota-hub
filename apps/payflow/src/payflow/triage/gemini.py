import json
import logging
import os
from typing import Any, Optional

from payflow.kb import KB
from payflow.models import Envelope, TriageResult
from payflow.triage.llm import _payload_to_result
from payflow.triage.prompt import TRIAGE_TOOL, build_system_prompt, build_user_message

logger = logging.getLogger("payflow.gemini")

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1h; Gemini's default. Extendable per-call.

# Same fields as Anthropic's TRIAGE_TOOL input_schema — Gemini's response_schema
# just consumes a JSON Schema directly.
TRIAGE_RESPONSE_SCHEMA = TRIAGE_TOOL["input_schema"]


class GeminiTriager:
    """Gemini-backed triager. Satisfies the same TriagerProtocol as LLMTriager.

    Prompt caching:
    - `use_cache=True` (default): create a cached_content for the KB+role system
      prompt on the first triage, reuse it for the rest of the triager's lifetime.
      Cuts per-envelope cost to ~1/2 of the uncached path (~10x cheaper than
      cached Anthropic Haiku 4.5 at typical NIP scale).
    - `use_cache=False`: send the full system prompt every call. Simpler, still
      cheaper than Anthropic per-token; use if you're on a model tier below
      Gemini's cache minimum-token threshold (currently 1024 tok for Flash-Lite).

    On any error during a cached call, we invalidate the cache and retry once —
    handles TTL expiry, cache-not-found, and permission drift uniformly.
    """

    def __init__(
        self,
        client: Any = None,
        model: str | None = None,
        max_tokens: int = 1024,
        use_cache: bool = True,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ):
        self.client = client or _default_client()
        self.model = model or os.environ.get("PAYFLOW_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.max_tokens = max_tokens
        self.use_cache = use_cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_name: Optional[str] = None

    def triage(self, env: Envelope, kb: KB) -> TriageResult:
        system_blocks = build_system_prompt(kb)
        system_text = "\n\n".join(b["text"] for b in system_blocks)
        user_text = build_user_message(env)

        if not self.use_cache:
            return self._triage_uncached(env, system_text, user_text)

        # Try cached path; on any failure, invalidate + retry once (uncached fallback
        # if cache recreation also fails, so a stuck cache never wedges triage entirely).
        try:
            return self._triage_cached(env, system_text, user_text)
        except Exception as e:
            logger.warning("cached triage failed (%s); invalidating cache and retrying", e)
            self._cached_name = None
            try:
                return self._triage_cached(env, system_text, user_text)
            except Exception as e2:
                logger.warning("retry with fresh cache also failed (%s); falling back to uncached", e2)
                return self._triage_uncached(env, system_text, user_text)

    def _triage_uncached(self, env: Envelope, system_text: str, user_text: str) -> TriageResult:
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
        return _payload_to_result(env, _extract_payload(response))

    def _triage_cached(self, env: Envelope, system_text: str, user_text: str) -> TriageResult:
        cache_name = self._ensure_cache(system_text)
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_text,
            config={
                "cached_content": cache_name,
                "response_mime_type": "application/json",
                "response_schema": TRIAGE_RESPONSE_SCHEMA,
                "max_output_tokens": self.max_tokens,
            },
        )
        return _payload_to_result(env, _extract_payload(response))

    def _ensure_cache(self, system_text: str) -> str:
        if self._cached_name is not None:
            return self._cached_name
        cache = self.client.caches.create(
            model=self.model,
            config={
                "system_instruction": system_text,
                "ttl": f"{self.cache_ttl_seconds}s",
                "display_name": "payflow-kb",
            },
        )
        self._cached_name = getattr(cache, "name", None) or cache["name"]
        return self._cached_name

    def invalidate_cache(self) -> None:
        """Force the next triage to recreate the cache. Test/ops helper."""
        self._cached_name = None


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
