import os
from typing import Any, Protocol

from payflow.kb import KB
from payflow.models import Envelope, Retryability, TriageResult
from payflow.triage.prompt import TRIAGE_TOOL, build_system_prompt, build_user_message

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class TriagerProtocol(Protocol):
    def triage(self, env: Envelope, kb: KB) -> TriageResult: ...


class LLMTriager:
    """Anthropic-backed triager. Fires only when the deterministic layer returns low confidence.

    The KB is serialized into the system prompt and marked for prompt caching, so per-call
    cost is dominated by the (small) envelope + tool-call output, not the KB.
    """

    def __init__(
        self,
        client: Any = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ):
        self.client = client or _default_client()
        self.model = model or os.environ.get("PAYFLOW_LLM_MODEL", DEFAULT_MODEL)
        self.max_tokens = max_tokens

    def triage(self, env: Envelope, kb: KB) -> TriageResult:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=build_system_prompt(kb),
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "record_triage"},
            messages=[{"role": "user", "content": build_user_message(env)}],
        )
        payload = _extract_tool_input(resp, "record_triage")
        return _payload_to_result(env, payload)


def _default_client() -> Any:
    """Lazy import so pytest doesn't need anthropic if only using a fake client."""
    from anthropic import Anthropic

    return Anthropic()


def _extract_tool_input(resp: Any, tool_name: str) -> dict:
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return dict(block.input)
    raise RuntimeError(
        f"LLM did not call {tool_name!r}. Response content: {resp.content!r}"
    )


def _payload_to_result(env: Envelope, payload: dict) -> TriageResult:
    strategy = Retryability(payload["retry_strategy"])
    return TriageResult(
        envelope=env,
        matched_code=None,
        cause=payload["cause"],
        action=payload["action"],
        evidence=list(payload.get("evidence") or []),
        retryable=strategy != Retryability.NEVER,
        retry_strategy=strategy,
        confidence=payload.get("confidence", "medium"),
    )
