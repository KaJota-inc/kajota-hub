import base64
from typing import Any, Optional

import httpx

from payflow.integrations.zendesk.config import ZendeskConfig


class ZendeskClient:
    """Thin Zendesk REST v2 client.

    Auth = HTTP Basic with `{email}/token:{api_token}` — note the `/token` suffix
    on the username. That's the Zendesk convention for API-token auth.
    """

    def __init__(self, config: ZendeskConfig, http: Optional[httpx.Client] = None):
        self.config = config
        auth = base64.b64encode(f"{config.email}/token:{config.api_token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "User-Agent": "payflow/0.1",
        }
        if http is None:
            self._http = httpx.Client(
                base_url=f"https://{config.subdomain}.zendesk.com",
                headers=headers,
                timeout=10.0,
            )
        else:
            # Injected clients (tests, custom transports) inherit our auth headers
            # so callers don't have to duplicate them.
            http.headers.update(headers)
            self._http = http

    def post_internal_comment(self, ticket_id: int | str, body: str) -> dict[str, Any]:
        """Add an internal (private) comment to a ticket.

        Zendesk uses ticket updates to add comments — no dedicated notes endpoint.
        `public: false` makes the comment internal-only (agents-only visibility).
        """
        r = self._http.put(
            f"/api/v2/tickets/{ticket_id}.json",
            json={"ticket": {"comment": {"body": body, "public": False}}},
        )
        r.raise_for_status()
        return r.json()

    def get_ticket(self, ticket_id: int | str) -> dict[str, Any]:
        r = self._http.get(f"/api/v2/tickets/{ticket_id}.json")
        r.raise_for_status()
        return r.json()

    def add_tags(self, ticket_id: int | str, tags: list[str]) -> dict[str, Any]:
        """Merge-add tags. Zendesk's PUT /tags.json REPLACES the array — we GET first,
        merge, then PUT the union. Never clobber existing tags."""
        current = self.get_ticket(ticket_id).get("ticket", {}).get("tags") or []
        merged = sorted(set(current) | set(tags))
        r = self._http.put(f"/api/v2/tickets/{ticket_id}/tags.json", json={"tags": merged})
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._http.close()
