"""Dispute triage — the one judgement in this system that rules can't make.

Everything else in Coach is deliberately deterministic: escrow state,
timeouts, amount caps, reputation counts are all facts you can compare,
and money movement should never depend on sampling temperature.

Free-text is different. A buyer writes "package arrived but the seal was
broken and two units are missing" and something has to decide whether
that is a dispute or a grumble. No rule table reads English. This is
where a model earns its place — and, crucially, its output is a
*classification that feeds a rule*, never a release decision.

The boundary that makes this safe:

    LLM  ->  is_dispute: bool, severity, category, summary
    rules ->  activeDispute = is_dispute  ->  verdict

The model can cause a HOLD or a REJECT. It can never cause a RELEASE:
`active_dispute=False` merely declines to block, and every other hard
rule still has to pass on its own. So the worst a bad classification can
do is stall a payout for a human to look at — the failure mode points at
caution, not at loss.

Falls back to a conservative keyword heuristic when Gemini is
unavailable, so the endpoint degrades instead of 500ing. The heuristic
is deliberately trigger-happy: over-flagging costs a human glance,
under-flagging costs the buyer's money.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any


# Words that make a complaint worth a human's attention even if the
# model is unreachable. Tuned for recall, not precision.
_HEURISTIC_TERMS = (
    "broken", "damaged", "missing", "never arrived", "not arrived", "didn't arrive",
    "did not arrive", "wrong item", "wrong product", "counterfeit", "fake",
    "refund", "scam", "fraud", "stolen", "empty box", "defective", "faulty",
    "not as described", "seal", "tampered", "leaking", "expired", "short",
)

_CATEGORIES = (
    "not_delivered",      # never showed up
    "damaged",            # arrived broken
    "wrong_item",         # not what was ordered
    "partial",            # short shipment
    "quality",            # arrived, works, but not as described
    "fraud",              # counterfeit / deliberate deception
    "other",
)


@dataclass(frozen=True)
class TriageResult:
    is_dispute: bool
    severity: str          # "none" | "low" | "medium" | "high"
    category: str          # one of _CATEGORIES
    summary: str           # one line, for the merchant
    classifier: str        # "llm" | "heuristic"
    confidence: float      # 0..1 — heuristic reports low on purpose

    def to_dict(self) -> dict[str, Any]:
        return {
            "isDispute": self.is_dispute,
            "severity": self.severity,
            "category": self.category,
            "summary": self.summary,
            "classifier": self.classifier,
            "confidence": round(self.confidence, 2),
        }


def _heuristic(message: str) -> TriageResult:
    """Keyword fallback. Biased toward flagging."""
    low = message.lower()
    hits = [t for t in _HEURISTIC_TERMS if t in low]
    if not hits:
        return TriageResult(
            is_dispute=False, severity="none", category="other",
            summary="No dispute language detected in the message.",
            classifier="heuristic", confidence=0.4,
        )
    if any(h in low for h in ("never arrived", "not arrived", "didn't arrive",
                              "did not arrive", "empty box")):
        category = "not_delivered"
    elif any(h in low for h in ("counterfeit", "fake", "scam", "fraud")):
        category = "fraud"
    elif any(h in low for h in ("broken", "damaged", "defective", "faulty", "leaking")):
        category = "damaged"
    elif any(h in low for h in ("wrong item", "wrong product")):
        category = "wrong_item"
    elif any(h in low for h in ("missing", "short")):
        category = "partial"
    else:
        category = "quality"
    return TriageResult(
        is_dispute=True,
        severity="high" if category in ("not_delivered", "fraud") else "medium",
        category=category,
        summary=f"Flagged on keyword match ({', '.join(hits[:3])}) — needs a human read.",
        classifier="heuristic", confidence=0.45,
    )


async def triage_message(message: str, *, prefer_llm: bool = True) -> TriageResult:
    """Classify a free-text buyer message into a dispute signal."""
    text = (message or "").strip()
    if not text:
        return TriageResult(
            is_dispute=False, severity="none", category="other",
            summary="Empty message — nothing to classify.",
            classifier="heuristic", confidence=1.0,
        )

    if not prefer_llm:
        return _heuristic(text)

    try:
        from google import genai
        from google.genai import types as gen_types

        client = genai.Client()
        prompt = (
            "You triage buyer messages for an escrow service. Decide whether "
            "this message is a DISPUTE — a claim that the goods were not "
            "delivered, damaged, wrong, incomplete, or misrepresented — as "
            "opposed to a question, a compliment, or a neutral remark.\n\n"
            "Reply with ONLY a JSON object, no prose, no code fence:\n"
            '{"is_dispute": bool, "severity": "none"|"low"|"medium"|"high", '
            f'"category": one of {list(_CATEGORIES)}, '
            '"summary": "one short sentence for the merchant", '
            '"confidence": 0.0-1.0}\n\n'
            "Bias toward flagging when genuinely ambiguous: a wrongly-flagged "
            "message costs a human thirty seconds, a missed dispute costs the "
            "buyer their money.\n\n"
            f"Buyer message:\n{text}"
        )
        cfg = gen_types.GenerateContentConfig(temperature=0.0, max_output_tokens=400)
        try:
            cfg.thinking_config = gen_types.ThinkingConfig(thinking_budget=0)
        except Exception:
            pass

        result = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
            contents=prompt,
            config=cfg,
        )
        raw = (result.text or "").strip()
        # Models occasionally fence the JSON despite instructions.
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return _heuristic(text)
        data = json.loads(m.group(0))

        category = data.get("category")
        if category not in _CATEGORIES:
            category = "other"
        severity = data.get("severity")
        if severity not in ("none", "low", "medium", "high"):
            severity = "medium" if data.get("is_dispute") else "none"

        return TriageResult(
            is_dispute=bool(data.get("is_dispute")),
            severity=severity,
            category=category,
            summary=str(data.get("summary") or "").strip()[:240] or "(no summary)",
            classifier="llm",
            confidence=float(data.get("confidence", 0.8)),
        )
    except Exception:
        # Vertex misconfigured, quota, bad JSON — degrade, never 500.
        return _heuristic(text)
