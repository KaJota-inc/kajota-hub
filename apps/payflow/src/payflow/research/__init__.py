"""Payflow as a research artefact.

Payflow instantiates three primitives relevant to the thesis
"Risk-Adaptive AI Infrastructure for Trustworthy Autonomous Financial Systems":

1. **Adaptive Inference** under heterogeneous decision costs.
   Confidence-routing policy (deterministic KB → LLM fallback → verifier) binds
   compute to the cost/risk profile of each decision. Not every triage warrants
   the same latency or token budget.
   → `payflow.triage.pipeline.triage`

2. **Bounded Autonomy** via a typed action space.
   `Retryability` is a fixed, enumerated action space; the adversarial verifier
   acts as a safety projector that maps unsafe LLM proposals back to the
   conservative subset (status_query). The Slack alert dispatcher is the
   human-in-the-loop escalation hook, invoked when the system refuses to act
   unilaterally.
   → `payflow.models.Retryability`, `payflow.triage.verifier.LLMVerifier`,
     `payflow.integrations._shared.alerts.AlertDispatcher`

3. **Grounded Verification** via evidence-citation contracts.
   The LLM triager must cite verbatim evidence from the input envelope (enforced
   by the structured output tool schema); the verifier rejects ungrounded
   proposals. This is "verification" in the Web2 sense; the Web3 extension is a
   natural next move — anchor evidence-commitment hashes on-chain for
   cross-institution replay-safe verification.
   → `payflow.triage.prompt.TRIAGE_TOOL`, `payflow.triage.verifier.LLMVerifier`

`generate_thesis_report()` runs a live eval on synthetic fixtures and emits the
numbers that back each primitive, intended as supplementary material for PhD /
MSc submissions. Reproducible: deterministic seed, fixed fixture count, pinned
model names.
"""
from payflow.research.report import (
    PrimitiveMetrics,
    ThesisReport,
    format_thesis_report,
    generate_thesis_report,
)

__all__ = [
    "PrimitiveMetrics",
    "ThesisReport",
    "format_thesis_report",
    "generate_thesis_report",
]
