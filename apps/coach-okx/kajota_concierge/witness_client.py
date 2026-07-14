"""Fire-and-forget POST hook to Kajota Witness.

When the Coach agent finishes a turn, we mirror the (user_message,
final_response) pair to Witness as a single encrypted chat blob on
0G Storage. This gives sellers durable, decentralised memory across
sessions — and gives Mesh escrow disputes a real evidence layer to
pull from.

Design notes
------------
- Fully optional. If WITNESS_URL is unset, _post_turn() is a no-op.
- Fire-and-forget. The POST runs in a background task; the chat
  response never waits on the Witness round-trip (~17s for a 0G
  upload). The mobile UI's user latency is unchanged.
- Soft-fail. If Witness is down or returns an error, we log a single
  line and move on. Coach must not break because the memory mirror
  is unavailable.
- No PII expansion. We send exactly what the existing /chat already
  returns (user message + agent response), no MongoDB documents,
  no MCP tool traces. Sensitivity is the same as the existing log
  stream.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover — guarded so import-time failures don't kill agent boot
    httpx = None  # type: ignore[assignment]


_WITNESS_URL = os.environ.get("WITNESS_URL", "").rstrip("/")
_WITNESS_SELLER_ID = os.environ.get("WITNESS_SELLER_ID", "kajota-concierge")
_WITNESS_TIMEOUT_S = float(os.environ.get("WITNESS_TIMEOUT_S", "60"))

_client: "httpx.AsyncClient | None" = None


def is_enabled() -> bool:
    """True iff Witness mirroring is configured and httpx is installed."""
    return bool(_WITNESS_URL) and httpx is not None


def _get_client() -> "httpx.AsyncClient | None":
    global _client
    if not is_enabled():
        return None
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(_WITNESS_TIMEOUT_S))
    return _client


def _build_payload(*, user_id: str, message: str, response: str) -> dict[str, Any]:
    """Map a Coach turn to a Witness ChatBlob."""
    return {
        "kind": "chat",
        "sellerId": _WITNESS_SELLER_ID,
        "buyerId": user_id,
        "ts": int(time.time() * 1000),
        "topic": f"concierge-turn-{user_id[:12]}",
        "messages": [
            {"role": "buyer", "text": message},
            {"role": "agent", "text": response},
        ],
    }


async def _post_now(*, user_id: str, message: str, response: str) -> dict[str, Any] | None:
    """Single POST, awaited. Returns the parsed JSON or None on failure.

    Used directly by the smoke script. The agent server calls
    post_turn_background() instead.
    """
    client = _get_client()
    if client is None:
        return None
    payload = _build_payload(user_id=user_id, message=message, response=response)
    try:
        resp = await client.post(f"{_WITNESS_URL}/memory", json=payload)
        if resp.status_code >= 400:
            print(
                f"[witness] {resp.status_code} {resp.text[:200]}",
                flush=True,
            )
            return None
        return resp.json()
    except Exception as exc:  # noqa: BLE001 — any network/timeout error
        print(f"[witness] post failed: {type(exc).__name__}: {exc}", flush=True)
        return None


def post_turn_background(*, user_id: str, message: str, response: str) -> None:
    """Schedule a Witness POST in the background. Returns immediately.

    Safe to call from any async handler — uses asyncio.create_task on
    the running loop. If Witness mirroring is disabled (no WITNESS_URL
    set, or httpx missing), this is a no-op.
    """
    if not is_enabled():
        return
    if not message or not response:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — caller is not in an async context. Skip
        # rather than spawning a new loop (would surprise the caller).
        return
    loop.create_task(
        _post_now(user_id=user_id, message=message, response=response),
        name="witness-mirror",
    )
