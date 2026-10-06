import os
from typing import Any, Protocol

from payflow.models import Envelope, Retryability, TriageResult
from payflow.triage.prompt import VERIFY_SYSTEM, VERIFY_TOOL, build_verifier_user_message

DEFAULT_VERIFIER_MODEL = "claude-sonnet-5"


class VerifierProtocol(Protocol):
    def verify(self, env: Envelope, result: TriageResult) -> TriageResult: ...


class LLMVerifier:
    """Adversarial-verify pass over a proposed triage result.

    Downgrades `confidence` to 'low' and forces `retry_strategy=status_query` if the
    verifier flags the proposal as ungrounded or unsafe. This is the safety rail that
    keeps a hallucinating primary triager from causing double-debits.
    """

    def __init__(
        self,
        client: Any = None,
        model: str | None = None,
        max_tokens: int = 512,
    ):
        self.client = client or _default_client()
        self.model = model or os.environ.get("PAYFLOW_VERIFIER_MODEL", DEFAULT_VERIFIER_MODEL)
        self.max_tokens = max_tokens

    def verify(self, env: Envelope, result: TriageResult) -> TriageResult:
        proposed = {
            "cause": result.cause,
            "action": result.action,
            "customer_message": result.matched_code.customer_message if result.matched_code else "",
            "retry_strategy": result.retry_strategy.value,
            "evidence": result.evidence,
            "confidence": result.confidence,
        }
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=VERIFY_SYSTEM,
            tools=[VERIFY_TOOL],
            tool_choice={"type": "tool", "name": "record_verdict"},
            messages=[{"role": "user", "content": build_verifier_user_message(env, proposed)}],
        )
        verdict = _extract_verdict(resp)
        if verdict["grounded"] and verdict["retry_safe"]:
            return result

        # Downgrade: unsafe or ungrounded → conservative fallback
        return result.model_copy(update={
            "confidence": "low",
            "retry_strategy": Retryability.STATUS_QUERY,
            "retryable": True,
            "action": (
                f"Verifier flagged proposal ({verdict['notes'] or 'no notes'}). "
                "Fallback: send TSQ and route to human ops."
            ),
            "evidence": [*result.evidence, f"verifier_notes={verdict['notes']!r}"],
        })


def _default_client() -> Any:
    from anthropic import Anthropic

    return Anthropic()


def _extract_verdict(resp: Any) -> dict:
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "record_verdict":
            return dict(block.input)
    raise RuntimeError(f"Verifier did not call record_verdict. Response: {resp.content!r}")
