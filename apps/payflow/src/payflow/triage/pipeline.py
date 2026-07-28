import os

from payflow.kb import KB
from payflow.models import Envelope, TriageResult
from payflow.triage.deterministic import triage_deterministic
from payflow.triage.llm import LLMTriager, TriagerProtocol
from payflow.triage.verifier import LLMVerifier, VerifierProtocol


def _default_triager() -> TriagerProtocol:
    """Provider picked by env: PAYFLOW_PROVIDER=anthropic|gemini (default: anthropic).

    Kept as a function so tests can monkey-patch or override cheaply.
    """
    provider = os.environ.get("PAYFLOW_PROVIDER", "anthropic").lower().strip()
    if provider == "gemini":
        from payflow.triage.gemini import GeminiTriager
        return GeminiTriager()
    if provider != "anthropic":
        raise ValueError(
            f"Unknown PAYFLOW_PROVIDER={provider!r}. Supported: anthropic, gemini."
        )
    return LLMTriager()


def triage(
    env: Envelope,
    kb: KB,
    *,
    use_llm: bool = False,
    verify: bool = False,
    llm_triager: TriagerProtocol | None = None,
    llm_verifier: VerifierProtocol | None = None,
) -> TriageResult:
    """Composed triage: deterministic → LLM fallback → optional verifier.

    - KB match on the (dialect, code) pair → return immediately (confidence=high).
    - Miss (unknown code or missing dialect) → LLM triage if `use_llm=True`, else return the
      low-confidence deterministic result. Primary triager picked by PAYFLOW_PROVIDER env
      (anthropic|gemini). Verifier stays Anthropic Sonnet 5 by default — safety-load-bearing
      role stays with the more skeptical model.
    - `verify=True` runs an adversarial verifier over the LLM output. Ungrounded or unsafe
      proposals are downgraded to `status_query` — the whole point being to never
      double-debit under model hallucination.
    """
    result = triage_deterministic(env, kb)
    if result.confidence == "high" or not use_llm:
        return result

    triager = llm_triager or _default_triager()
    result = triager.triage(env, kb)

    if verify:
        verifier = llm_verifier or LLMVerifier()
        result = verifier.verify(env, result)

    return result
