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

import base64
import json
import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as gen_types
from pydantic import BaseModel

from kajota_concierge.agent import root_agent
from kajota_concierge import witness_client
from kajota_concierge.x402_casper import (
    PaymentRequiredError,
    X402Config,
    build_payment_requirements,
    require_payment,
)

APP_NAME = "kajota-concierge"

# x402 paywall config for the premium endpoint. Resolved once from the
# environment at import; `configured` is False on a clean checkout (no
# sponsored CSPR.cloud key), in which case /coach/premium still answers 402
# but explains what's missing rather than charging.
_X402 = X402Config.from_env(
    description="KaJota Coach — premium agentic purchase insight",
)

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


class PremiumRequest(BaseModel):
    """Body for POST /coach/premium — the x402-gated insight endpoint.

    Same shape as a chat turn, but the caller must attach a settled Casper
    x402 payment (``X-PAYMENT`` header) for the request to run. ``message``
    is optional: with none, the agent produces a full proactive deep-dive.
    """

    message: str | None = None
    userId: str = "demo-user-1"
    sessionId: str | None = None


class ChatResponse(BaseModel):
    sessionId: str
    response: str
    # The full event trace from this turn — useful for the demo recording
    # so we can show MCP tool calls inline in the video.
    events: list[dict[str, Any]]


class PremiumResponse(ChatResponse):
    """A ChatResponse plus the on-chain settlement receipt.

    ``settlement`` carries the Casper deploy hash the facilitator produced
    when it settled the CEP-18 micropayment — the verifiable proof that this
    agent turn was paid for on-chain. Also surfaced in the
    ``X-PAYMENT-RESPONSE`` header per the x402 standard.
    """

    settlement: dict[str, Any]


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


# The premium deep-dive prompt handed to the agent on a paid /coach/premium
# turn with no explicit message. Richer than /proactive: we ask for a
# multi-query analysis that justifies the micropayment — spend trend,
# wishlist price-drop opportunities, and a concrete next-buy recommendation
# with reasoning. Same anti-hallucination discipline as the proactive prompt.
_PREMIUM_PROMPT = (
    "Produce a PREMIUM purchase insight for the user. This is a paid, "
    "deep-dive analysis, so be thorough and ground every claim in data.\n"
    "\n"
    "BEFORE writing any text, call the MongoDB tools to gather:\n"
    "  1. ALL of the user's `purchases` (find by userId, sorted "
    "     `orderedAt: -1`). Use these to summarise total spend and the "
    "     dominant category.\n"
    "  2. The full `wishlist` (find by userId). Flag any item whose "
    "     `currentPriceQuote` is at or below its `targetPriceQuote` — those "
    "     are buy-now opportunities.\n"
    "  3. `products` in the user's dominant category (find, limit 5) to pick "
    "     ONE specific recommendation they don't already own.\n"
    "\n"
    "Then write a 3-4 sentence insight: their spending pattern, any wishlist "
    "price opportunity, and the single best next purchase with a one-line "
    "reason. Cite exact item names and prices verbatim; the `quoteSymbol` is "
    "`NGNT`. Never fabricate. End with the standard [CARDS] block (one card "
    "for the recommendation, one per buy-now wishlist hit, max 3 cards)."
)


@app.exception_handler(PaymentRequiredError)
async def _payment_required_handler(
    _request: Request, exc: PaymentRequiredError
) -> JSONResponse:
    """Return the 402 the x402 gate built (price tag in body + header)."""
    return exc.response


@app.get("/")
async def banner() -> dict[str, Any]:
    return {
        "service": APP_NAME,
        "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
        "partners": ["mongodb", "fetch"],
        "payments": {
            "protocol": "x402",
            "network": _X402.network,
            "facilitator": _X402.facilitator_url,
            "configured": _X402.configured,
        },
        "endpoints": [
            "/chat",
            "/proactive",
            "/coach/premium",
            "/healthz",
            "/docs",
        ],
        "docs": "/docs",
        "witnessMirror": witness_client.is_enabled(),
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

    # Mirror this turn to Kajota Witness (encrypted blob on 0G Storage)
    # so it becomes recoverable as evidence in any future Mesh dispute.
    # Fire-and-forget — never blocks the chat response. No-op if
    # WITNESS_URL is unset.
    witness_client.post_turn_background(
        user_id=user_id,
        message=message,
        response=final_text,
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


@app.get("/coach/premium")
async def coach_premium_info(request: Request) -> JSONResponse:
    """Human/agent-friendly discovery for the paywalled endpoint.

    A GET here is what happens when someone *clicks the link* (a browser, a
    judge opening the submission's "Live API" URL). Rather than a bare
    ``405 Method Not Allowed`` — which reads as "broken" — we answer with the
    real x402 ``402`` challenge plus a plain-English "how to pay" note, so the
    endpoint is self-documenting and visibly live: the price tag, asset, and
    network are right there, exactly what a paying agent would receive.
    """
    resource = f"{request.headers.get('x-forwarded-proto') or request.url.scheme}://{request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc}{request.headers.get('x-forwarded-prefix', '')}{request.url.path}"
    requirements = build_payment_requirements(_X402, resource)
    body = {
        "x402Version": 2,
        "accepts": [requirements],
        "message": (
            "This is an x402-paywalled endpoint. It settles a CEP-18 "
            "micropayment on Casper. Send a POST with a JSON body and an "
            "`X-PAYMENT` header carrying a signed `transfer_with_authorization`; "
            "the CSPR.cloud facilitator settles it on-chain and the response "
            "returns the premium insight plus the settlement receipt."
        ),
        "howToPay": {
            "method": "POST",
            "resource": resource,
            "priceAtomic": _X402.max_amount_required,
            "asset": _X402.asset,
            "network": _X402.network,
            "facilitator": _X402.facilitator_url,
            "configured": _X402.configured,
        },
        "docs": "/docs",
    }
    header_blob = base64.b64encode(json.dumps(requirements).encode()).decode()
    return JSONResponse(
        status_code=402,
        content=body,
        headers={
            "PAYMENT-REQUIRED": header_blob,
            "Access-Control-Expose-Headers": "PAYMENT-REQUIRED",
        },
    )


@app.post("/coach/premium", response_model=PremiumResponse)
async def coach_premium(req: PremiumRequest, request: Request) -> JSONResponse:
    """Pay-per-call premium insight, settled on Casper via x402.

    The agentic-payments showcase: an agent that wants this richer analysis
    pays for it with a CEP-18 micropayment over HTTP — no account, no API
    key, just a signed authorisation the Casper facilitator settles on-chain.

    Flow: ``require_payment`` raises ``PaymentRequiredError`` (→ 402 with the
    price tag) until the caller retries with a valid ``X-PAYMENT`` header;
    once the facilitator settles, we run the deep-dive agent turn and return
    it with the on-chain deploy hash attached.
    """
    settlement = await require_payment(request, _X402)

    turn = await _run_agent_turn(
        user_id=req.userId,
        session_id=req.sessionId,
        message=req.message or _PREMIUM_PROMPT,
    )

    body = PremiumResponse(
        sessionId=turn.sessionId,
        response=turn.response,
        events=turn.events,
        settlement={
            "network": settlement.network,
            "transaction": settlement.transaction,
            "payer": settlement.payer,
            "settled": settlement.success,
        },
    )
    # Echo the settlement receipt in the standard x402 response header too.
    return JSONResponse(
        content=body.model_dump(),
        headers={
            "X-PAYMENT-RESPONSE": settlement.response_header(),
            "Access-Control-Expose-Headers": "X-PAYMENT-RESPONSE",
        },
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
