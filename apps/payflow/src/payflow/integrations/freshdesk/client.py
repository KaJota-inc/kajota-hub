import base64
from typing import Any, Optional

import httpx

from payflow.integrations.freshdesk.config import FreshdeskConfig


class FreshdeskClient:
    """Thin Freshdesk REST v2 client. Auth = HTTP Basic (api_key : X)."""

    def __init__(self, config: FreshdeskConfig, http: Optional[httpx.Client] = None):
        self.config = config
        auth = base64.b64encode(f"{config.api_key}:X".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "User-Agent": "payflow/0.1",
        }
        if http is None:
            self._http = httpx.Client(
                base_url=f"https://{config.domain}",
                headers=headers,
                timeout=10.0,
            )
        else:
            http.headers.update(headers)
            self._http = http

    def post_private_note(self, ticket_id: int | str, body: str) -> dict[str, Any]:
        r = self._http.post(
            f"/api/v2/tickets/{ticket_id}/notes",
            json={"body": body, "private": True},
        )
        r.raise_for_status()
        return r.json()

    def get_ticket(self, ticket_id: int | str) -> dict[str, Any]:
        r = self._http.get(f"/api/v2/tickets/{ticket_id}")
        r.raise_for_status()
        return r.json()

    def add_tags(self, ticket_id: int | str, tags: list[str]) -> dict[str, Any]:
        """Merge-add tags. Fetches current tags first so we don't clobber existing ones."""
        current = self.get_ticket(ticket_id).get("tags") or []
        merged = sorted(set(current) | set(tags))
        r = self._http.put(f"/api/v2/tickets/{ticket_id}", json={"tags": merged})
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._http.close()
