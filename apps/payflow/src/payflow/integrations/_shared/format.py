from payflow.models import TriageResult

_CONFIDENCE_LABEL = {
    "high":   "HIGH CONFIDENCE",
    "medium": "MEDIUM CONFIDENCE",
    "low":    "LOW CONFIDENCE — ROUTE TO HUMAN OPS",
}


def format_triage_note(result: TriageResult) -> str:
    """Format a TriageResult as a helpdesk private note (Markdown).

    Vendor-agnostic. Freshdesk private notes and Zendesk internal comments both
    accept Markdown. Structured so ops can skim in <10 seconds AND downstream
    automation can parse the footer for tags/metrics.
    """
    r = result
    env = r.envelope
    conf = _CONFIDENCE_LABEL.get(r.confidence, r.confidence)

    lines: list[str] = [
        f"## Payflow triage — {conf}",
        "",
        f"**Cause:** {r.cause}",
        f"**Ops action:** {r.action}",
        f"**Retry strategy:** `{r.retry_strategy.value}` "
        f"({'retryable' if r.retryable else 'terminal — do not retry'})",
    ]

    if r.matched_code is not None:
        lines.append(f"**Category:** `{r.matched_code.category.value}`")
        lines.append(f"**Customer-safe message:** {r.matched_code.customer_message}")

    if r.evidence:
        lines.extend(["", "**Evidence:**"])
        lines.extend(f"- {e}" for e in r.evidence)

    lines.extend([
        "",
        "---",
        (
            f"<sub>payflow · dialect={env.dialect.value if env.dialect else 'n/a'} "
            f"· method={env.method or 'n/a'} · session={env.session_id or 'n/a'} "
            f"· source={env.source} · retry={r.retry_strategy.value} · confidence={r.confidence}</sub>"
        ),
    ])
    return "\n".join(lines)
