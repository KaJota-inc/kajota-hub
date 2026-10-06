import logging
from typing import Optional

from payflow.integrations._shared.observability import incr
from payflow.integrations.slack.client import SlackClient
from payflow.integrations.slack.config import SlackAlertConfig
from payflow.integrations.slack.format import build_alert_payload, should_alert
from payflow.models import TriageResult

logger = logging.getLogger("payflow.alerts")


class AlertDispatcher:
    """Fire out-of-band alerts for high-risk predictions.

    No-op if `slack_config` is None — the whole subsystem is opt-in. Failures
    are logged and counted but never propagate: alerts are observability, not
    load-bearing on the triage reply.
    """

    def __init__(
        self,
        slack_config: Optional[SlackAlertConfig] = None,
        slack_client: Optional[SlackClient] = None,
    ):
        self.slack_config = slack_config
        if slack_client is not None:
            self.slack_client = slack_client
        elif slack_config is not None:
            self.slack_client = SlackClient(slack_config)
        else:
            self.slack_client = None

    def dispatch(
        self,
        result: TriageResult,
        *,
        integration: str,
        ticket_id: Optional[int | str] = None,
        ticket_url: Optional[str] = None,
    ) -> bool:
        """Returns True if an alert was sent, False if filtered or disabled."""
        if self.slack_config is None or self.slack_client is None:
            return False
        if not should_alert(result, self.slack_config):
            return False
        payload = build_alert_payload(
            result, ticket_id=ticket_id, ticket_url=ticket_url, integration=integration,
        )
        try:
            self.slack_client.post(payload)
            incr(
                "slack_alert_sent_total",
                integration=integration,
                strategy=result.retry_strategy.value,
                confidence=result.confidence,
            )
            logger.info("slack_alert_sent", extra={
                "integration": integration,
                "ticket_id": ticket_id,
                "strategy": result.retry_strategy.value,
                "confidence": result.confidence,
            })
            return True
        except Exception as e:  # noqa: BLE001
            incr("slack_alert_failed_total", integration=integration)
            logger.warning("slack_alert_failed", extra={
                "integration": integration,
                "ticket_id": ticket_id,
                "error": str(e),
            })
            return False
