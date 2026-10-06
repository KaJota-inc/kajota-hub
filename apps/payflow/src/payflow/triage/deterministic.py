from payflow.kb import KB, lookup
from payflow.models import Envelope, Retryability, TriageResult


def triage_deterministic(env: Envelope, kb: KB) -> TriageResult:
    """KB-only lookup. Returns confidence='high' on a match, 'low' otherwise.

    The LLM layer only fires when this returns 'low' — the whole product ethos is
    'deterministic decides, LLM explains'.
    """
    if env.response_code is None or env.dialect is None:
        return TriageResult(
            envelope=env,
            cause="Missing response code or dialect — cannot triage deterministically.",
            action="Escalate to LLM triage or ops review.",
            retryable=False,
            retry_strategy=Retryability.NEVER,
            confidence="low",
        )

    entry = lookup(kb, env.dialect, env.response_code)
    if entry is None:
        return TriageResult(
            envelope=env,
            cause=f"Code {env.response_code!r} not found in {env.dialect.value} KB.",
            action="Escalate to LLM triage; consider adding this code to the KB.",
            evidence=[f"response_message={env.response_message!r}"] if env.response_message else [],
            retryable=False,
            retry_strategy=Retryability.NEVER,
            confidence="low",
        )

    evidence: list[str] = []
    if env.response_message:
        evidence.append(f"response_message={env.response_message!r}")
    if env.method:
        evidence.append(f"method={env.method!r}")
    evidence.append(f"({env.dialect.value},{env.response_code}) → {entry.raw_message!r}")

    return TriageResult(
        envelope=env,
        matched_code=entry,
        cause=entry.raw_message,
        action=entry.ops_action,
        evidence=evidence,
        retryable=entry.retry != Retryability.NEVER,
        retry_strategy=entry.retry,
        confidence="high",
    )


triage_envelope = triage_deterministic
