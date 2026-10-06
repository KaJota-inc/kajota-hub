import os
from typing import Optional

from pydantic import BaseModel, Field


class SlackAlertConfig(BaseModel):
    """Opt-in Slack alerting. If no webhook URL is set, nothing fires.

    `min_amount_ngn` gates strategy-based alerts; low-confidence predictions always
    alert because they need a human by definition.
    """
    webhook_url: str = Field(..., description="Slack incoming webhook URL.")
    min_amount_ngn: float = Field(50_000.0, description="Amount threshold for strategy-based alerts.")
    strategies: list[str] = Field(
        default_factory=lambda: ["never", "status_query", "reversal"],
        description="Retry strategies worth alerting on when amount >= min_amount_ngn.",
    )
    alert_on_low_confidence: bool = Field(
        True,
        description="Fire regardless of amount or strategy when confidence='low'.",
    )

    @classmethod
    def from_env(cls) -> Optional["SlackAlertConfig"]:
        url = os.environ.get("SLACK_WEBHOOK_URL")
        if not url:
            return None
        strategies_raw = os.environ.get("SLACK_ALERT_STRATEGIES", "never,status_query,reversal")
        return cls(
            webhook_url=url,
            min_amount_ngn=float(os.environ.get("SLACK_ALERT_MIN_AMOUNT_NGN", "50000")),
            strategies=[s.strip() for s in strategies_raw.split(",") if s.strip()],
            alert_on_low_confidence=_bool_env("SLACK_ALERT_ON_LOW_CONFIDENCE", True),
        )


def _bool_env(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")
