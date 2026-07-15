"""Expose Kajota Coach's capabilities as an MCP server.

We already CONSUME MCP (the ADK agent composes MongoDB MCP + Fetch
MCP). This module serves Coach's own domain capabilities BACK OUT as
MCP tools so other agents — Claude Desktop, Cursor, a downstream ADK
build, or Slack's own Agent Builder runtime — can call:

    add_to_watchlist(product)               — MongoDB insert-one
    get_status()                            — proactive turn output
    resolve_listing_id(hint)                — on-chain registry read
    propose_escrow(hint, amount)            — stage a deposit (dry-run)
    settle_escrow(hint, amount)             — sign + broadcast both txs

Transport is HTTP (Streamable HTTP) so the server can be reached
without a local pipe. Mounted at `/mcp` on the FastAPI process by
server.py — clients hit
`https://kajota-hub.onrender.com/slack/mcp`.

The MCP surface deliberately mirrors the Slack surface: same
capabilities, different transport. That's the "one agent, three
transports" story — mobile (`/chat`), Slack (`/slack/*`), and MCP
(`/mcp`) — all sharing the same tools, sessions, and mesh client.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from kajota_concierge.mesh import (
    MeshCallError,
    MeshConfigError,
    resolve_listing_id_display,
    send_approve,
    send_deposit,
)


_LOG = logging.getLogger("kajota_concierge.mcp")


mcp = FastMCP(
    name="kajota-coach",
    # stateless_http lets a fresh POST with no session header still get
    # a valid initialize response. Trades multi-turn session state for
    # zero-config connectivity — right choice for a demo server where
    # every /kajota-coach call is a fresh one-shot tool invocation
    # anyway.
    stateless_http=True,
    json_response=True,
    instructions=(
        "Kajota Coach exposes co-selling operations as MCP tools. Use "
        "`get_status` to summarise a merchant's recent activity, "
        "`add_to_watchlist` to persist a product to the wishlist, "
        "`resolve_listing_id` to look up a Mesh registry entry, "
        "`propose_escrow` to dry-run a USDC deposit (calldata only, no "
        "broadcast), and `settle_escrow` to sign + broadcast the two-tx "
        "sequence on Mantle Sepolia via the demo relayer. `settle_escrow` "
        "requires MESH_RELAYER_PRIVATE_KEY to be set on the server side."
    ),
)


@mcp.tool()
async def resolve_listing_id(product_hint: str) -> dict[str, Any]:
    """Look up a bytes32 listing id in the Mesh CosellRegistry.

    Args:
        product_hint: The product id as registered on-chain (e.g.
            'yeezy-hoodie'). The registry stores listings under a hash
            of (productId, wholesaler, coseller); this call returns the
            first match's listingId so callers can pre-flight before
            proposing an escrow.

    Returns a dict with `listing_id` (0x-prefixed hex) or raises if the
    registry has no listing for that hint.
    """
    try:
        return {
            "product_hint": product_hint,
            "listing_id": resolve_listing_id_display(product_hint),
            "chain": os.environ.get("MESH_CHAIN", "mantle-sepolia"),
        }
    except MeshCallError as exc:
        raise RuntimeError(f"listing_not_registered: {exc}") from exc
    except MeshConfigError as exc:
        raise RuntimeError(f"mesh_config_missing: {exc}") from exc


@mcp.tool()
async def propose_escrow(
    product_hint: str, gross_amount_usdc: float
) -> dict[str, Any]:
    """Stage a USDC escrow deposit WITHOUT broadcasting.

    Useful for a downstream agent that wants to confirm listing id +
    amount with a human before actually spending funds. Returns the
    listing id and computed base-unit amount; call `settle_escrow` with
    the same args to actually broadcast.
    """
    try:
        listing_id = resolve_listing_id_display(product_hint)
    except MeshCallError as exc:
        raise RuntimeError(f"listing_not_registered: {exc}") from exc
    except MeshConfigError as exc:
        raise RuntimeError(f"mesh_config_missing: {exc}") from exc
    return {
        "product_hint": product_hint,
        "listing_id": listing_id,
        "gross_amount_usdc": gross_amount_usdc,
        "gross_amount_base_units": int(gross_amount_usdc * 1_000_000),
        "chain": os.environ.get("MESH_CHAIN", "mantle-sepolia"),
        "broadcasted": False,
        "note": (
            "This is a dry-run. Call settle_escrow with the same "
            "product_hint + gross_amount_usdc to broadcast the "
            "USDC.approve + CosellEscrow.deposit sequence."
        ),
    }


@mcp.tool()
async def settle_escrow(
    product_hint: str, gross_amount_usdc: float
) -> dict[str, Any]:
    """Sign + broadcast the two-tx USDC escrow deposit sequence.

    Runs USDC.approve → wait for receipt → CosellEscrow.deposit →
    wait for receipt from the server-configured demo relayer. Returns
    both explorer URLs.

    Requires MESH_RELAYER_PRIVATE_KEY on the server; raises otherwise.
    Downstream agents should surface a human-approval step before
    calling this — an unattended MCP client should NOT auto-settle
    without an operator in the loop.
    """
    try:
        approve = send_approve(
            listing_hint=product_hint, gross_amount_usdc=gross_amount_usdc
        )
        deposit = send_deposit(
            listing_hint=product_hint, gross_amount_usdc=gross_amount_usdc
        )
    except MeshConfigError as exc:
        raise RuntimeError(f"mesh_config_missing: {exc}") from exc
    except MeshCallError as exc:
        raise RuntimeError(f"tx_failed: {exc}") from exc
    return {
        "product_hint": product_hint,
        "gross_amount_usdc": gross_amount_usdc,
        "chain": os.environ.get("MESH_CHAIN", "mantle-sepolia"),
        "approve": {
            "hash": approve.hash,
            "explorer_url": approve.explorer_url,
            "status": approve.status,
        },
        "deposit": {
            "hash": deposit.hash,
            "explorer_url": deposit.explorer_url,
            "status": deposit.status,
        },
    }


# The Slack surface reuses `_run_agent_turn` from server.py. Rather
# than pull the same coroutine into the MCP tools by import (which
# would create a circular import), the MCP wrappers below build a
# thin coroutine at call time via a late-bound helper populated in
# server.py at import time.

_run_agent_turn = None  # type: ignore[assignment]


def bind_agent_runner(run_agent_turn) -> None:
    """Called by server.py to plug the ADK Runner into the MCP tools.

    Kept out of module-level to avoid a circular import between
    kajota_concierge.mcp_server and kajota_concierge.server.
    """
    global _run_agent_turn
    _run_agent_turn = run_agent_turn


_STATUS_PROMPT = (
    "BEFORE producing any text, you MUST call the MongoDB `find` tool "
    "exactly three times: (1) `purchases` sorted by orderedAt desc "
    "limit 1; (2) `wishlist` no limit; (3) `products` limit 3. Then "
    "produce a 1-2 sentence personalised status referring to the ACTUAL "
    "data (real item names, prices, `NGNT` quoteSymbol). End with a "
    "[CARDS] block built from the queried documents. Do NOT fabricate."
)


@mcp.tool()
async def get_status(user_id: str = "demo-user-1") -> dict[str, Any]:
    """Fire a proactive agent turn — recent orders, wishlist, drops.

    Returns the plain-text status + the raw ADK event trace. Handy for
    a downstream agent that wants a full ADK reasoning trace, not just
    a natural-language string.
    """
    if _run_agent_turn is None:
        raise RuntimeError(
            "agent_runner_not_bound: kajota_concierge.mcp_server was "
            "loaded without server.bind_agent_runner() — the FastAPI "
            "app must call bind_agent_runner at import time."
        )
    reply = await _run_agent_turn(
        user_id=f"mcp:{user_id}",
        session_id=f"mcp:{user_id}",
        message=_STATUS_PROMPT,
    )
    return {"response": reply.response, "events": reply.events}


@mcp.tool()
async def add_to_watchlist(
    product: str, user_id: str = "demo-user-1"
) -> dict[str, Any]:
    """Persist a product to the merchant's MongoDB wishlist.

    Delegates to the ADK agent so the same MongoDB MCP path used by
    Slack `/kajota watch` handles the write. Returns the agent's
    confirmation text plus the raw event trace.
    """
    if _run_agent_turn is None:
        raise RuntimeError("agent_runner_not_bound: see get_status")
    message = (
        f"Add '{product}' to my watchlist. Use the MongoDB MCP "
        f"`insert-one` on the `wishlist` collection with "
        f"{{userId:'{user_id}', itemName:'{product}'}}. Reply with a "
        "1-sentence confirmation."
    )
    reply = await _run_agent_turn(
        user_id=f"mcp:{user_id}",
        session_id=f"mcp:{user_id}",
        message=message,
    )
    return {"response": reply.response, "events": reply.events}


def streamable_http_app():
    """Return an ASGI app for the streamable-http MCP transport.

    server.py mounts this under `/mcp` so clients like Claude Desktop
    can reach https://<host>/mcp as an MCP server.
    """
    return mcp.streamable_http_app()
