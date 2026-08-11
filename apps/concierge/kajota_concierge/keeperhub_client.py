"""Thin async client for the KeeperHub REST API.

Purpose: fire a pre-created KeeperHub workflow that calls
``CosellEscrow.release(depositId)`` on Ethereum Sepolia via the web3
plugin's ``write-contract`` step. KeeperHub handles retries, gas
pricing, and the on-chain submission from the Turnkey keeper wallet
that we set as the escrow's ``releaseAuth``.

Design choice: the workflow is created **once** (via the KeeperHub UI or
a one-off setup script) with ``depositId`` declared as a workflow input.
The client here just triggers it per request — that keeps this file
small, keeps the sensitive workflow definition inside KeeperHub's UI
audit trail, and avoids re-creating a workflow every release.

Env:
    KEEPERHUB_API_KEY          — org-scope API key ``kh_...``
    KEEPERHUB_WORKFLOW_ID      — id of the pre-created release workflow
    KEEPERHUB_BASE_URL         — override for staging (default prod)
    KEEPERHUB_TIMEOUT_SECONDS  — HTTP timeout (default 30)
    KEEPERHUB_POLL_SECONDS     — max seconds to wait for tx hash
                                 (default 60)
    KEEPERHUB_POLL_INTERVAL    — seconds between poll checks (default 3)
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://app.keeperhub.com"


@dataclass(frozen=True)
class KeeperHubConfig:
    """Resolved KeeperHub client settings."""

    base_url: str
    api_key: str
    workflow_id: str
    timeout_seconds: int
    poll_seconds: int
    poll_interval_seconds: int

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.workflow_id)

    @classmethod
    def from_env(cls) -> "KeeperHubConfig":
        """Resolve from the environment.

        Falls back to the ``KH_*`` names the Node escrow app on this same
        host already sets, so deploying this client needs no duplicate
        secrets — the key and workflow id in Render are reused as-is. The
        ``KEEPERHUB_*`` names win when both are present.
        """
        first = lambda *names: next(
            (v for v in (os.environ.get(n, "").strip() for n in names) if v), ""
        )
        return cls(
            base_url=(
                first("KEEPERHUB_BASE_URL", "KH_API_BASE", "KH_BASE") or DEFAULT_BASE_URL
            ).rstrip("/"),
            api_key=first("KEEPERHUB_API_KEY", "KH_API_KEY", "KH_KEY"),
            workflow_id=first("KEEPERHUB_WORKFLOW_ID", "KH_WORKFLOW_ID"),
            timeout_seconds=int(os.environ.get("KEEPERHUB_TIMEOUT_SECONDS", "30")),
            poll_seconds=int(os.environ.get("KEEPERHUB_POLL_SECONDS", "60")),
            poll_interval_seconds=int(
                os.environ.get("KEEPERHUB_POLL_INTERVAL", "3")
            ),
        )


@dataclass(frozen=True)
class KeeperExecution:
    """One execution of the release workflow — the keeper's receipt."""

    execution_id: str
    status: str
    transaction_hash: str = ""
    network: str = ""
    block_number: int = 0
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status in {"success", "succeeded", "completed"} and bool(
            self.transaction_hash
        )

    @property
    def failed(self) -> bool:
        return self.status in {"failed", "error", "cancelled"}

    @property
    def terminal(self) -> bool:
        return self.succeeded or self.failed


class KeeperHubError(Exception):
    """Raised when KeeperHub returns a non-2xx or the poll times out."""


class KeeperHubClient:
    """Async KeeperHub REST client — the Coach agent's execution edge."""

    def __init__(self, cfg: KeeperHubConfig) -> None:
        self._cfg = cfg

    # Read-only passthroughs so callers can report configuration state
    # without reaching into a private attribute. The API key is
    # deliberately not exposed — only whether one is present.
    @property
    def configured(self) -> bool:
        return self._cfg.configured

    @property
    def workflow_id(self) -> str:
        return self._cfg.workflow_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Fetch a workflow definition (nodes + edges + config) by id.

        Used by the auditor endpoint — Coach reads the workflow via KH's
        own REST surface and runs it through the rules engine before the
        merchant ever fires it. Raises :class:`KeeperHubError` on any
        non-2xx or empty body.
        """
        if not self._cfg.api_key:
            raise KeeperHubError("KeeperHub client is not configured (KEEPERHUB_API_KEY)")
        async with httpx.AsyncClient(timeout=self._cfg.timeout_seconds) as client:
            resp = await client.get(
                f"{self._cfg.base_url}/api/workflows/{workflow_id}",
                headers=self._headers(),
            )
            if resp.status_code >= 300:
                raise KeeperHubError(
                    f"get_workflow HTTP {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
            if not isinstance(data, dict):
                raise KeeperHubError(
                    f"unexpected KH workflow response shape: {type(data).__name__}"
                )
            return data

    async def trigger_release(self, deposit_id: str) -> KeeperExecution:
        """Fire the pre-created release workflow with the given depositId.

        Returns the terminal :class:`KeeperExecution`. Polls until the
        keeper reports a tx hash or the configured poll window elapses.
        """
        if not self._cfg.configured:
            raise KeeperHubError(
                "KeeperHub client is not configured "
                "(set KEEPERHUB_API_KEY and KEEPERHUB_WORKFLOW_ID)."
            )
        body = {
            # Workflow input parameters. The pre-created workflow declares
            # `depositId` in its inputSchema; KeeperHub substitutes this
            # value into the web3/write-contract action's `args`.
            "inputs": {"depositId": deposit_id},
        }
        async with httpx.AsyncClient(timeout=self._cfg.timeout_seconds) as client:
            resp = await client.post(
                f"{self._cfg.base_url}/api/workflows/"
                f"{self._cfg.workflow_id}/execute",
                headers=self._headers(),
                json=body,
            )
            if resp.status_code >= 300:
                raise KeeperHubError(
                    f"trigger HTTP {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
            execution_id = str(
                data.get("id") or data.get("executionId") or ""
            )
            if not execution_id:
                # Some responses inline a status-only body until the
                # queued execution appears — poll the executions list.
                execution_id = await self._latest_execution_id(client)
            return await self._await_terminal(client, execution_id)

    async def _latest_execution_id(self, client: httpx.AsyncClient) -> str:
        resp = await client.get(
            f"{self._cfg.base_url}/api/workflows/"
            f"{self._cfg.workflow_id}/executions?limit=1",
            headers=self._headers(),
        )
        if resp.status_code >= 300:
            raise KeeperHubError(
                f"executions HTTP {resp.status_code}: {resp.text[:300]}"
            )
        rows = resp.json()
        if not rows:
            raise KeeperHubError("no execution appeared after trigger")
        row = rows[0]
        return str(row.get("id") or row.get("executionId") or "")

    async def _await_terminal(
        self, client: httpx.AsyncClient, execution_id: str
    ) -> KeeperExecution:
        deadline_ticks = max(1, self._cfg.poll_seconds // max(
            1, self._cfg.poll_interval_seconds
        ))
        last: KeeperExecution = KeeperExecution(
            execution_id=execution_id, status="pending"
        )
        for _ in range(deadline_ticks + 1):
            resp = await client.get(
                f"{self._cfg.base_url}/api/workflows/"
                f"{self._cfg.workflow_id}/executions/{execution_id}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                # Race: execution not yet indexed — wait and retry.
                await asyncio.sleep(self._cfg.poll_interval_seconds)
                continue
            if resp.status_code >= 300:
                raise KeeperHubError(
                    f"poll HTTP {resp.status_code}: {resp.text[:300]}"
                )
            row = resp.json()
            last = _row_to_execution(execution_id, row)
            if last.terminal:
                return last
            await asyncio.sleep(self._cfg.poll_interval_seconds)
        # Timed out — return what we have; caller decides how to surface it.
        return last


def _row_to_execution(execution_id: str, row: dict[str, Any]) -> KeeperExecution:
    """Best-effort mapping of KeeperHub's execution payload to our dataclass.

    Field names vary a little across the API surface (``status`` vs
    ``state``, ``txHash`` vs ``transactionHash``). We accept both.
    """
    status = str(row.get("status") or row.get("state") or "pending")
    tx = str(
        row.get("transactionHash")
        or row.get("txHash")
        or row.get("transaction")
        or ""
    )
    # KeeperHub can nest action outputs under `steps[]` — the tx hash of
    # the release action lives there. Walk the steps to find the first
    # non-empty tx if we didn't get one at the top level.
    if not tx:
        for step in row.get("steps", []) or []:
            step_output = step.get("output") or {}
            candidate = str(
                step_output.get("transactionHash")
                or step_output.get("txHash")
                or step_output.get("transaction")
                or ""
            )
            if candidate:
                tx = candidate
                break
    return KeeperExecution(
        execution_id=execution_id,
        status=status,
        transaction_hash=tx,
        network=str(row.get("network") or row.get("chainId") or ""),
        block_number=int(row.get("blockNumber") or 0),
        error=str(row.get("errorMessage") or row.get("error") or ""),
    )
