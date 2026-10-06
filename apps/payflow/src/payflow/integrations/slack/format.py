from typing import Optional

from payflow.integrations.slack.config import SlackAlertConfig
from payflow.models import TriageResult


def should_alert(result: TriageResult, config: SlackAlertConfig) -> bool:
    """Decide whether to fire a Slack alert for this triage result.

    Rules (in order):
    1. If confidence='low' and alert_on_low_confidence=True → alert.
       Low-confidence always needs a human; amount gate does not apply.
    2. If retry_strategy not in config.strategies → skip (not interesting).
    3. If envelope.amount is unknown → alert (err on the side of surfacing).
    4. If amount >= min_amount_ngn → alert, else skip.
    """
    if config.alert_on_low_confidence and result.confidence == "low":
        return True
    if result.retry_strategy.value not in set(config.strategies):
        return False
    amount = result.envelope.amount
    if amount is None:
        return True
    return amount >= config.min_amount_ngn


def build_alert_payload(
    result: TriageResult,
    *,
    ticket_id: Optional[int | str] = None,
    ticket_url: Optional[str] = None,
    integration: Optional[str] = None,
) -> dict:
    """Format a TriageResult as a Slack Block Kit payload.

    Includes a `text` fallback so Slack notifications on mobile render usefully
    even without block rendering.
    """
    r = result
    env = r.envelope
    amount_str = f"NGN {env.amount:,.2f}" if env.amount is not None else "unknown"
    title = _title_for(r)

    ticket_line = ""
    if ticket_id is not None:
        if ticket_url:
            ticket_line = f"#{ticket_id} (<{ticket_url}|open>)"
        else:
            ticket_line = f"#{ticket_id}"

    fields = [
        ("Amount", amount_str),
        ("Dialect", env.dialect.value if env.dialect else "n/a"),
        ("Response code", env.response_code or "n/a"),
        ("Retry strategy", f"`{r.retry_strategy.value}`"),
        ("Confidence", r.confidence),
    ]
    if ticket_line:
        fields.append(("Ticket", ticket_line))

    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": title}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*{k}:*\n{v}"} for k, v in fields
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Cause:* {r.cause}\n*Ops action:* {r.action}"
        }},
    ]
    context_bits = [
        f"payflow · session=…{(env.session_id or '')[-6:] if env.session_id else 'n/a'}",
        f"method={env.method or 'n/a'}",
    ]
    if integration:
        context_bits.append(f"integration={integration}")
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": " · ".join(context_bits)}],
    })
    return {"text": title, "blocks": blocks}


def _title_for(r: TriageResult) -> str:
    if r.confidence == "low":
        return "Payflow: LOW CONFIDENCE triage — human review required"
    labels = {
        "never": "Payflow: terminal failure",
        "status_query": "Payflow: TSQ required (do not retry)",
        "reversal": "Payflow: reversal required",
        "backoff": "Payflow: retry with backoff",
        "immediate": "Payflow: safe immediate retry",
    }
    return labels.get(r.retry_strategy.value, f"Payflow: {r.retry_strategy.value}")
