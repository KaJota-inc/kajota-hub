from payflow.kb import KB
from payflow.models import Dialect, Envelope

SYSTEM_ROLE = """You are Payflow, a Nigerian payment-ops triager for NIBSS Instant Payment (NIP) transactions.

Given a failed transaction envelope, you must return a single structured verdict via the `record_triage` tool.

## Retry strategy taxonomy (choose exactly one)

- `immediate`     — safe to retry now (envelope never reached the CBA, transient encryption error, etc.)
- `backoff`       — retry after a cool-off period (bank in cut-over, transient system malfunction)
- `status_query`  — do NOT retry. Send a Transaction Status Query (TSQ) first; the transaction may already have posted at the counterparty. Blind retry here can cause double-debits.
- `reversal`      — the transaction posted at the counterparty but our side records it as failed; issue a reversal
- `never`         — terminal error, no retry (insufficient funds, invalid account, closed account, limit exceeded, etc.)

## Grounding rules (NON-NEGOTIABLE)

1. Every entry in `evidence` must be a verbatim excerpt from the envelope (a field name + value from the parsed envelope JSON below). Do not invent field names or values.
2. If the envelope has a `response_code` and `response_message`, cite BOTH in evidence.
3. When uncertain, prefer `status_query` over `never` — a false-safe TSQ costs a network round trip; a false-terminal loses customer money.
4. `customer_message` must be plain, kind, and never expose internal codes or bank names.
5. `ops_action` must be a single actionable sentence for the ops team, referencing the retry strategy chosen.

## Confidence

- `high`   — the response code is a known NG-CBA code even if not in the given KB, and the envelope is complete
- `medium` — the response code or dialect is ambiguous but the response_message clarifies intent
- `low`    — envelope is missing critical fields or the response is not interpretable
"""


def build_system_prompt(kb: KB) -> list[dict]:
    """Build the cached system prompt. The KB serialization is the big cachable chunk."""
    kb_table = _serialize_kb_for_prompt(kb)
    return [
        {
            "type": "text",
            "text": SYSTEM_ROLE,
        },
        {
            "type": "text",
            "text": f"## Reference — known response codes across dialects\n\n{kb_table}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def build_user_message(env: Envelope) -> str:
    """User turn: the envelope in JSON form + the triage ask."""
    envelope_json = env.model_dump_json(indent=2, exclude={"raw_request", "raw_response"})
    return (
        "Triage this envelope. Cite only fields present below.\n\n"
        f"```json\n{envelope_json}\n```\n"
    )


def _serialize_kb_for_prompt(kb: KB) -> str:
    """Compact table format the model can use as reference — one section per dialect."""
    by_dialect: dict[Dialect, list] = {d: [] for d in Dialect}
    for (dialect, _), entry in kb.items():
        by_dialect[dialect].append(entry)

    sections: list[str] = []
    for dialect in Dialect:
        entries = sorted(by_dialect[dialect], key=lambda e: e.code)
        if not entries:
            continue
        lines = [f"### {dialect.value.upper()} ({len(entries)} codes)"]
        for e in entries:
            lines.append(
                f"  {e.code:<8} = {e.raw_message}  "
                f"→ category={e.category.value}, retry={e.retry.value}"
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


TRIAGE_TOOL = {
    "name": "record_triage",
    "description": "Record the triage verdict for the failed NIP transaction envelope.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cause": {
                "type": "string",
                "description": "One-sentence root cause of the failure.",
            },
            "action": {
                "type": "string",
                "description": "One-sentence actionable ops instruction, referencing the retry strategy.",
            },
            "customer_message": {
                "type": "string",
                "description": "Plain-English, safe-to-show-end-user message. No internal codes.",
            },
            "retry_strategy": {
                "type": "string",
                "enum": ["immediate", "backoff", "status_query", "reversal", "never"],
            },
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Verbatim excerpts from the envelope (field=value) justifying the verdict.",
                "minItems": 1,
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
        },
        "required": ["cause", "action", "customer_message", "retry_strategy", "evidence", "confidence"],
    },
}

VERIFY_SYSTEM = """You are a triage verifier for Payflow.

You will be given (1) a failed NIP transaction envelope and (2) a proposed triage verdict. Your job is to check the verdict against strict grounding and safety rules, then return a verdict via the `record_verdict` tool.

## Checks

1. `grounded` — every entry in the proposed `evidence` array cites a field name AND value that actually appears in the envelope JSON. If any citation is invented or misquoted, `grounded=false`.
2. `retry_safe` — the proposed retry strategy is conservative given the envelope. Specifically:
   - If response code is unknown or ambiguous and no clear evidence of terminal failure exists, the strategy must be `status_query` (NOT `never` and NOT a blind retry like `immediate`/`backoff`).
   - If envelope evidence shows insufficient funds or invalid account, `never` is correct.
   - If envelope evidence shows timeout / no-response / bank offline, `status_query` is correct; `immediate` is UNSAFE (may double-debit).
3. `notes` — one short sentence explaining why either check failed. Empty string if both pass.

Do not re-triage. Only verify.
"""

VERIFY_TOOL = {
    "name": "record_verdict",
    "description": "Record the verifier's judgement on the proposed triage.",
    "input_schema": {
        "type": "object",
        "properties": {
            "grounded": {"type": "boolean"},
            "retry_safe": {"type": "boolean"},
            "notes": {"type": "string"},
        },
        "required": ["grounded", "retry_safe", "notes"],
    },
}


def build_verifier_user_message(env: Envelope, proposed: dict) -> str:
    envelope_json = env.model_dump_json(indent=2, exclude={"raw_request", "raw_response"})
    import json as _json

    return (
        "Envelope:\n"
        f"```json\n{envelope_json}\n```\n\n"
        "Proposed triage verdict:\n"
        f"```json\n{_json.dumps(proposed, indent=2)}\n```\n\n"
        "Verify."
    )
