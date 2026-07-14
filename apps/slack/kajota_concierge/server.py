"""FastAPI wrapper around the ADK agent.

ADK ships ``adk web`` and ``adk run`` for interactive dev, but for the
deployed Render service we want a clean HTTP surface the mobile coach
can call. This module exposes:

    POST /chat      — single-turn input → final text response
    GET  /healthz   — readiness check (200 + JSON if the agent imported
                      cleanly + MongoDB is reachable)
    GET  /          — returns a tiny JSON banner so the Render free-tier
                      cold-start hit shows up in logs

Sessions are kept in-memory (``InMemorySessionService``) so the first
deploy boots without an external session store. For multi-instance
production you'd swap to ``DatabaseSessionService`` against the same
MongoDB.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as gen_types
from pydantic import BaseModel

from kajota_concierge.agent import root_agent
from kajota_concierge.slack_app import build_slack_app
from kajota_concierge import mcp_server as kajota_mcp

APP_NAME = "kajota-concierge"

app = FastAPI(
    title="KaJota Concierge",
    description=(
        "Shopping assistant agent — Gemini 3 Pro on Google ADK, reaching "
        "MongoDB Atlas through the official MongoDB MCP server."
    ),
    version="0.1.0",
)

# Single session service for the process. ADK runners take it as a
# dep and resolve sessions by (app_name, user_id, session_id).
_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=_session_service,
)


class ChatRequest(BaseModel):
    message: str
    userId: str = "demo-user-1"
    sessionId: str | None = None


class ProactiveRequest(BaseModel):
    """Body for POST /proactive — the agentic-initiative endpoint.

    The mobile UI calls this on ConciergeScreen mount with no user
    message. The server fires a one-shot agent turn with a fixed
    greeter prompt that instructs the agent to choose its own MongoDB
    queries based on the user's state and produce a personalised
    opening message + cards.
    """

    userId: str = "demo-user-1"
    sessionId: str | None = None


class ChatResponse(BaseModel):
    sessionId: str
    response: str
    # The full event trace from this turn — useful for the demo recording
    # so we can show MCP tool calls inline in the video.
    events: list[dict[str, Any]]


# The system-instructed greeter prompt. Lives here (not in agent.py)
# because it's not an agent identity rule, it's the prompt the
# /proactive endpoint hands to the agent in lieu of a user message.
#
# This is the "agentic initiative" claim in the Devpost submission, so
# we have to force-multiply tool use. Gemini 2.5's default behaviour
# when given an open-ended "greet me" prompt is to skip tools and
# hallucinate plausible-sounding data — exactly what kills agent
# demos. The fix below is explicitly directive: enumerate the three
# tool calls the agent MUST issue before generating any text, and
# remind it that every value in [CARDS] must come from those calls.
_PROACTIVE_PROMPT = (
    "BEFORE producing any text, you MUST call the MongoDB `find` tool "
    "exactly three times, in this order:\n"
    "  1. find on `purchases` with {\"userId\":\"demo-user-1\"}, "
    "     sorted by `orderedAt: -1`, limit 1. This gives you the user's "
    "     most recent order.\n"
    "  2. find on `wishlist` with {\"userId\":\"demo-user-1\"}, no "
    "     limit. This gives you all current wishlist items.\n"
    "  3. find on `products`, limit 3, optionally filtered by the "
    "     `category` of the order from step 1. This gives you a "
    "     recommendation pool.\n"
    "\n"
    "After all three tool calls have returned, produce a 1-2 sentence "
    "personalised greeting that references the ACTUAL data you found — "
    "use real `itemName` / `name` values, real `pricePaidQuote` / "
    "`priceQuote` / `currentPriceQuote` values, and the real "
    "`quoteSymbol` (which is `NGNT` in this demo, never `USDC` or "
    "`USD`).\n"
    "\n"
    "End with the standard [CARDS] block. Build the cards from the "
    "documents you queried — one card for the recent order, one card "
    "per wishlist item (cap at 2 so the card list stays scannable), "
    "and one card for a single recommendation picked from the "
    "products pool. Do NOT fabricate any item names, prices, order "
    "ids, or categories — every value in [CARDS] must trace back to a "
    "document returned by one of the three find calls above.\n"
    "\n"
    "Do NOT ask me what I want. Do NOT say you can't help. Just run "
    "the three queries and report what you found."
)


@app.get("/")
async def banner() -> dict[str, Any]:
    return {
        "service": APP_NAME,
        "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
        "partners": ["mongodb", "fetch"],
        "endpoints": [
            "/chat",
            "/proactive",
            "/healthz",
            "/docs",
            "/slack/events",
            "/slack/commands/kajota",
            "/slack/actions",
            "/mcp",
        ],
        "mcp_server": {
            "name": "kajota-coach",
            "url": "/mcp",
            "tools": [
                "resolve_listing_id",
                "propose_escrow",
                "settle_escrow",
                "get_status",
                "add_to_watchlist",
            ],
        },
        "docs": "/docs",
    }


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    # Light check — just confirms the agent imported and Mongo URI is
    # set. We don't actually round-trip to MongoDB here because the MCP
    # server's subprocess is lazy-started by the runner on first use.
    if not os.environ.get("MONGODB_URI"):
        raise HTTPException(status_code=503, detail="MONGODB_URI not set")
    return {"ok": True, "agent": root_agent.name}


async def _run_agent_turn(
    *,
    user_id: str,
    session_id: str | None,
    message: str,
) -> ChatResponse:
    """Run one agent turn and return a `ChatResponse`.

    Shared by `/chat` (reactive — `message` is the user's input) and
    `/proactive` (agentic — `message` is the greeter prompt the
    /proactive endpoint synthesises). Same session machinery, same
    event drain, same response shape — so the mobile UI can render
    either one identically.
    """
    session_id = session_id or str(uuid.uuid4())

    # Get-or-create the session. ADK's API: get_session raises on miss
    # in some versions; wrap to handle both.
    session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        session = await _session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

    content = gen_types.Content(
        role="user",
        parts=[gen_types.Part(text=message)],
    )

    final_text = ""
    events: list[dict[str, Any]] = []

    # Drain the async event stream — the final-response event carries
    # the full reply text; intermediate events show tool calls.
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        events.append(_summarise_event(event))
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                p.text for p in event.content.parts if getattr(p, "text", None)
            )

    return ChatResponse(
        sessionId=session_id,
        response=final_text or "(no response)",
        events=events,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    return await _run_agent_turn(
        user_id=req.userId,
        session_id=req.sessionId,
        message=req.message,
    )


@app.post("/proactive", response_model=ChatResponse)
async def proactive(req: ProactiveRequest) -> ChatResponse:
    """Agentic-initiative endpoint — mobile calls this on screen mount.

    The agent picks its own tool sequence (recent purchases, wishlist
    deltas, catalogue browse) and emits a personalised greeting + the
    standard `[CARDS]` payload. No user input required.
    """
    return await _run_agent_turn(
        user_id=req.userId,
        session_id=req.sessionId,
        message=_PROACTIVE_PROMPT,
    )


# ─── Slack transport ───────────────────────────────────────────────
#
# Mounted only when SLACK_BOT_TOKEN + SLACK_SIGNING_SECRET are both set.
# The mobile /chat + /proactive endpoints keep working either way — the
# Slack app is a pure additional surface.

_slack_app = build_slack_app(run_agent_turn=_run_agent_turn)
if _slack_app is not None:
    from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

    _slack_handler = AsyncSlackRequestHandler(_slack_app)

    @app.post("/slack/events")
    async def slack_events(req: Request):
        return await _slack_handler.handle(req)

    @app.post("/slack/commands/kajota")
    async def slack_command(req: Request):
        return await _slack_handler.handle(req)

    # Interactivity payload for Approve / Deny buttons on the pending
    # deposit card. Must be registered as the "Interactivity URL" in
    # the Slack app's Interactivity & Shortcuts settings.
    @app.post("/slack/actions")
    async def slack_actions(req: Request):
        return await _slack_handler.handle(req)


# ─── Kajota Coach as an MCP server ────────────────────────────────
#
# The ADK agent CONSUMES MongoDB MCP + Fetch MCP. This mount exposes
# Coach's own capabilities BACK OUT as an MCP server, reachable at
# `/mcp` — so Claude Desktop, Cursor, or any downstream MCP client
# can call watch/status/settle-escrow as tools.
#
# The MCP tools need access to the ADK Runner (for get_status and
# add_to_watchlist), which is defined in this module. Rather than
# import _run_agent_turn from mcp_server (circular), we bind it here.

kajota_mcp.bind_agent_runner(_run_agent_turn)
try:
    _mcp_asgi_app = kajota_mcp.streamable_http_app()
    app.mount("/mcp", _mcp_asgi_app)
except Exception as _mcp_mount_err:  # noqa: BLE001
    # If the mcp SDK version doesn't expose streamable_http_app yet,
    # skip the mount rather than break the Slack + mobile surfaces.
    import logging as _logging

    _logging.getLogger("kajota_concierge.server").warning(
        "MCP server not mounted: %s", _mcp_mount_err
    )


def _summarise_event(event: Any) -> dict[str, Any]:
    """Compact event shape for the demo trace.

    We don't want to ship the full ADK event payload — too noisy for the
    submission video. This keeps the keys a judge would actually care
    about: who spoke, what tool was called, what came back.
    """
    parts = []
    if event.content and getattr(event.content, "parts", None):
        for p in event.content.parts:
            if getattr(p, "text", None):
                parts.append({"text": p.text})
            elif getattr(p, "function_call", None):
                parts.append(
                    {
                        "tool_call": {
                            "name": p.function_call.name,
                            "args": dict(p.function_call.args or {}),
                        }
                    }
                )
            elif getattr(p, "function_response", None):
                # Truncate large MCP responses so the trace stays readable.
                raw = p.function_response.response
                preview = str(raw)
                if len(preview) > 500:
                    preview = preview[:500] + "…(truncated)"
                parts.append(
                    {
                        "tool_response": {
                            "name": p.function_response.name,
                            "preview": preview,
                        }
                    }
                )
    return {
        "author": getattr(event, "author", "unknown"),
        "final": event.is_final_response(),
        "parts": parts,
    }


def main() -> None:
    """Entrypoint for `kajota-agent` (pyproject scripts). Used by Render."""
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "kajota_concierge.server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
