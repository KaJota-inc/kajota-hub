from typing import Optional

import httpx

from payflow.integrations.slack.config import SlackAlertConfig


class SlackClient:
    """Minimal incoming-webhook client. One method: `post(payload)`.

    Slack webhook responses are 200 OK with body `ok` or 400+ with an error body.
    `post` raises on 4xx/5xx so the caller can bump a failed-alert counter.
    """

    def __init__(self, config: SlackAlertConfig, http: Optional[httpx.Client] = None):
        self.config = config
        self._http = http if http is not None else httpx.Client(timeout=5.0)

    def post(self, payload: dict) -> int:
        r = self._http.post(self.config.webhook_url, json=payload)
        r.raise_for_status()
        return r.status_code

    def close(self) -> None:
        self._http.close()
