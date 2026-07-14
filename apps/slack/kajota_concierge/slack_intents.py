"""Pending on-chain intents awaiting a Slack team-member approval.

The /kajota pay command doesn't broadcast immediately — it stashes a
pending deposit intent here and posts a Block Kit card with
Approve/Deny buttons in-channel. Another workspace member clicks
Approve → the button handler pops the intent from this store, runs
the mesh.send_approve → mesh.send_deposit sequence, and posts
threaded status updates for each on-chain step.

The store is in-memory. On Render's free-tier single worker that's
fine; if you scale to multiple workers, swap for a Redis-backed store
keyed on the same intent id. Pending intents that sit unclaimed for
15 min are pruned by `sweep_stale()` — called opportunistically on
every put/get to keep the map bounded without a background task.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass


PENDING_TTL_SECONDS = 15 * 60


@dataclass
class PendingDeposit:
    intent_id: str
    listing_hint: str
    gross_amount_usdc: float
    requested_by_user_id: str  # slack user id, e.g. U0…
    requested_by_display: str  # human name we surface in the card
    team_id: str
    channel_id: str
    listing_id_display: str  # 0x-prefixed for the card
    created_at: float


_INTENTS: dict[str, PendingDeposit] = {}
_LOCK = threading.Lock()


def _sweep_stale_locked(now: float) -> None:
    stale = [
        k for k, v in _INTENTS.items() if now - v.created_at > PENDING_TTL_SECONDS
    ]
    for k in stale:
        _INTENTS.pop(k, None)


def new_intent_id() -> str:
    # 8 bytes → 16 hex chars. Collision-free for the demo's blast radius.
    return "d_" + secrets.token_hex(8)


def put(intent: PendingDeposit) -> None:
    now = time.time()
    with _LOCK:
        _sweep_stale_locked(now)
        _INTENTS[intent.intent_id] = intent


def take(intent_id: str) -> PendingDeposit | None:
    """Pop the intent. Returns None if unknown or expired."""
    now = time.time()
    with _LOCK:
        _sweep_stale_locked(now)
        return _INTENTS.pop(intent_id, None)


def peek(intent_id: str) -> PendingDeposit | None:
    now = time.time()
    with _LOCK:
        _sweep_stale_locked(now)
        return _INTENTS.get(intent_id)
