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
from fastapi.responses import HTMLResponse, JSONResponse
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
from kajota_concierge.coach_cfo import (
    ReleaseSignals,
    evaluate as evaluate_release,
)
from kajota_concierge.coach_auditor import audit_workflow
from kajota_concierge.coach_triage import triage_message

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
            "/coach/should-release",
            "/coach/audit-workflow",
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


# ---- Coach CFO + KH workflow auditor ------------------------------
#
# Two endpoints ported from the kajota-coach hackathon/keeperhub branch
# so they ride the same Render deployment as the rest of the concierge.
# The rules engines and narration modules (`coach_cfo.py`,
# `coach_auditor.py`) are byte-for-byte copies of the coach-repo
# versions; 34 tests in `tests/` cover them.

class ShouldReleaseRequest(BaseModel):
    """Body for POST /coach/should-release — CFO verdict on a proposed release."""

    depositId: str
    escrowState: str = "held"
    buyer: str = "0x0000000000000000000000000000000000000000"
    seller: str = "0x0000000000000000000000000000000000000000"
    grossAmountRaw: int = 100_000            # 0.10 USDC default
    listingId: str = "0x" + "00" * 32
    depositedAt: int | None = None
    now: int | None = None
    buyerConfirmed: bool = True
    sellerShipped: bool = True
    activeDispute: bool = False
    priorSuccessfulReleases: int = 10
    priorDisputes: int = 0
    maxAmountRaw: int = 10_000_000_000
    preferLLM: bool = True


class ShouldReleaseResponse(BaseModel):
    depositId: str
    decision: str
    why: str
    narrator: str
    rules: list[dict[str, Any]]
    signals: dict[str, Any]


class AuditWorkflowRequest(BaseModel):
    """Body for POST /coach/audit-workflow — static audit of a KH workflow."""

    workflow: dict[str, Any]
    workflowRef: str | None = None


class AuditWorkflowResponse(BaseModel):
    passed: bool
    counts: dict[str, int]
    issues: list[dict[str, Any]]
    summary: str
    actionNodesScanned: int
    workflowRef: str


@app.get("/coach/should-release")
async def coach_should_release_info() -> dict[str, Any]:
    """Self-describing GET for browser clicks — real work happens on POST.

    A person clicking the endpoint URL in Discord / a submission / a
    tweet lands here and sees what the endpoint does, what body it
    expects, and a curl example — instead of the FastAPI default
    `{"detail":"Method Not Allowed"}` which reads as broken.
    """
    return {
        "endpoint": "/coach/should-release",
        "method": "POST",
        "purpose": (
            "Coach as the merchant's autonomous CFO. Runs a deterministic "
            "rules engine over the deposit's signals and returns a verdict "
            "(release / hold / reject) plus plain-English narration. "
            "Deterministic decides, LLM/template explains."
        ),
        "requestBody": {
            "depositId": "0x… (required)",
            "grossAmountRaw": "int, USDC atomic units",
            "buyerConfirmed": "bool",
            "sellerShipped": "bool",
            "activeDispute": "bool",
            "priorSuccessfulReleases": "int",
            "priorDisputes": "int",
            "preferLLM": "bool, default true",
        },
        "curlExample": (
            "curl -X POST https://kajota-hub.onrender.com/concierge/coach/should-release "
            "-H 'content-type: application/json' "
            "-d '{\"depositId\":\"0xe713d5a3eb6c0c3c247e3c86ad23696e006c6097de47d5fad9a303838f0f2d13\",\"grossAmountRaw\":100000,\"buyerConfirmed\":true,\"sellerShipped\":true,\"activeDispute\":false,\"preferLLM\":false}'"
        ),
        "interactiveDemo": "https://kajota-hub.onrender.com/keeperhub#coach",
        "sourceRepo": "https://github.com/KaJota-inc/kajota-coach",
        "sourceModule": "agent/kajota_concierge/coach_cfo.py",
        "swaggerUi": "/concierge/docs",
    }


@app.post("/coach/should-release", response_model=ShouldReleaseResponse)
async def coach_should_release(req: ShouldReleaseRequest) -> ShouldReleaseResponse:
    """Coach as the merchant's autonomous CFO — the AGENT decides.

    Runs a deterministic rules engine over the deposit's signals and
    returns one of three verdicts (release / hold / reject) with plain
    -English reasoning. No release fires from this call — it's the
    decision layer that sits IN FRONT of KeeperHub, not the executor.

    Design invariant: deterministic decides, narration explains.
    The Gemini narrator downgrades cleanly to template narration when
    Vertex isn't configured. Every evaluated rule is returned so a
    downstream audit can see exactly why Coach called it the way it did.
    """
    import time as _time

    now = req.now if req.now is not None else int(_time.time())
    deposited_at = req.depositedAt if req.depositedAt is not None else now - 3600
    signals = ReleaseSignals(
        deposit_id=req.depositId,
        escrow_state=req.escrowState,
        buyer=req.buyer,
        seller=req.seller,
        gross_amount_raw=req.grossAmountRaw,
        listing_id=req.listingId,
        deposited_at=deposited_at,
        now=now,
        buyer_confirmed=req.buyerConfirmed,
        seller_shipped=req.sellerShipped,
        active_dispute=req.activeDispute,
        prior_successful_releases_for_seller=req.priorSuccessfulReleases,
        prior_disputes_against_seller=req.priorDisputes,
        max_amount_raw=req.maxAmountRaw,
    )
    verdict = await evaluate_release(signals, prefer_llm=req.preferLLM)
    return ShouldReleaseResponse(
        depositId=req.depositId,
        decision=verdict.decision,
        why=verdict.why,
        narrator=verdict.narrator,
        rules=[r.to_dict() for r in verdict.rules],
        signals=verdict.signals.to_dict(),
    )


# The browser-facing page for the auditor endpoint. Served when the
# caller says it wants HTML; API clients still get JSON from the same
# URL. A person following a link from Discord or a submission lands on
# something explorable — schema, a paste-and-run curl, and a try-it form
# that POSTs back to this very endpoint — instead of a wall of JSON.
_AUDIT_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>POST /coach/audit-workflow · Kajota Coach</title><style>
:root{--bg:#050507;--elev:#0c0c11;--edge:#1a1a22;--edge2:#2a2a36;--fg:#f5f5f7;
--dim:#6b7280;--mint:#00ff9c;--blood:#ff2d3f;--yellow:#ffe042;--accent:#81d9ff;
--mono:ui-monospace,"JetBrains Mono","SF Mono",Menlo,monospace;
--disp:-apple-system,"SF Pro Display",Inter,system-ui,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font:15px/1.6 var(--disp);
background-image:linear-gradient(#101019 1px,transparent 1px),linear-gradient(90deg,#101019 1px,transparent 1px);
background-size:48px 48px;background-attachment:fixed;min-height:100vh}
.wrap{max-width:920px;margin:0 auto;padding:48px 24px 96px}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
code{font-family:var(--mono);font-size:13px}
.crumb{font-family:var(--mono);font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);margin-bottom:20px}
h1{font-size:34px;letter-spacing:-0.02em;line-height:1.1;margin-bottom:8px}
h1 .verb{font-family:var(--mono);font-size:13px;font-weight:700;letter-spacing:1.5px;
background:var(--mint);color:var(--bg);padding:5px 11px;border-radius:2px;vertical-align:middle;margin-right:12px}
.sub{color:var(--dim);font-size:16px;max-width:660px;margin-bottom:14px}
.live{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:10px;
letter-spacing:1.2px;text-transform:uppercase;color:var(--mint);margin-bottom:36px}
.live::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--mint);
box-shadow:0 0 10px var(--mint);animation:p 1.6s ease-in-out infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.35}}
h2{font-size:12px;font-family:var(--mono);letter-spacing:1.8px;text-transform:uppercase;
color:var(--dim);margin:40px 0 14px;padding-bottom:10px;border-bottom:1px solid var(--edge)}
pre{background:#000;border:1px solid var(--edge);padding:16px 18px;font-family:var(--mono);
font-size:12.5px;line-height:1.7;overflow-x:auto;position:relative}
.k{color:var(--yellow)}.s{color:var(--mint)}.n{color:var(--accent)}.c{color:var(--dim)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-family:var(--mono);font-size:10px;color:var(--dim);text-transform:uppercase;
letter-spacing:1.5px;padding:0 14px 10px 0;border-bottom:1px solid var(--edge)}
td{padding:12px 14px 12px 0;border-bottom:1px solid var(--edge);vertical-align:top}
tr:last-child td{border-bottom:none}
.f{font-family:var(--mono);color:var(--yellow);white-space:nowrap}
.t{font-family:var(--mono);color:var(--accent);font-size:12px;white-space:nowrap}
.d{color:var(--dim);line-height:1.5}
.req{color:var(--blood);font-size:10px;font-family:var(--mono);letter-spacing:1px}
textarea{width:100%;min-height:190px;background:#000;border:1px solid var(--edge);color:var(--fg);
font-family:var(--mono);font-size:12.5px;padding:14px 16px;line-height:1.6;resize:vertical;outline:none}
textarea:focus{border-color:var(--mint)}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:14px}
button{font-family:var(--mono);font-size:12px;letter-spacing:1px;text-transform:uppercase;
font-weight:600;padding:12px 20px;border-radius:2px;border:1px solid var(--edge2);
background:var(--elev);color:var(--fg);cursor:pointer;transition:all .15s}
button:hover{border-color:var(--fg)}
button.go{background:var(--mint);color:var(--bg);border-color:var(--mint)}
button.go:hover{background:transparent;color:var(--mint)}
button:disabled{opacity:.4;cursor:not-allowed}
.hint{color:var(--dim);font-size:13px;margin-top:10px}
.banner{padding:15px 18px;border-radius:2px;font-family:var(--mono);font-size:13px;font-weight:600}
.pass{border:1px solid var(--mint);background:rgba(0,255,156,.08);color:var(--mint)}
.fail{border:1px solid var(--blood);background:rgba(255,45,63,.08);color:var(--blood)}
.iss{border:1px solid var(--edge);padding:13px 15px;margin-top:10px;font-size:13.5px;line-height:1.55}
.iss.error{border-color:var(--blood);background:rgba(255,45,63,.06)}
.iss.warn{border-color:var(--yellow);background:rgba(255,224,66,.06)}
.iss.info{border-color:var(--accent);background:rgba(129,217,255,.06)}
.iss .hd{display:flex;justify-content:space-between;gap:12px;margin-bottom:7px;
font-family:var(--mono);font-size:10px;letter-spacing:1.4px;text-transform:uppercase}
.iss .fix{font-family:var(--mono);font-size:12px;color:var(--mint);margin-top:7px}
footer{margin-top:56px;padding-top:22px;border-top:1px solid var(--edge);
font-family:var(--mono);font-size:11px;color:var(--dim);letter-spacing:1px;
display:flex;gap:18px;flex-wrap:wrap}
</style></head><body><div class="wrap">

<div class="crumb">Kajota Coach · agent API</div>
<h1><span class="verb">POST</span>/coach/audit-workflow</h1>
<p class="sub">Second-opinion audit for a KeeperHub <code style="color:var(--yellow)">web3/write-contract</code>
workflow. Catches every trap documented in our merged bounty PR
<a href="https://github.com/KeeperHub/keeperhub/pull/1857" target="_blank">KeeperHub/keeperhub#1857</a>,
plus a few adjacent ones. Purely diagnostic — it never signs or writes anything.</p>
<span class="live">live · this page is served by the endpoint itself</span>

<h2>Try it</h2>
<textarea id="in" spellcheck="false"></textarea>
<div class="row">
  <button class="go" id="run">Send request</button>
  <button id="bad">Load broken workflow</button>
  <button id="good">Load correct workflow</button>
</div>
<p class="hint">Posts to this exact URL from your browser. Nothing is stored.</p>
<div id="out" style="margin-top:20px"></div>

<h2>Request body</h2>
<pre><span class="c">// Content-Type: application/json</span>
{
  <span class="k">"workflow"</span>: { <span class="c">/* the KH workflow definition, verbatim */</span>
    <span class="k">"name"</span>:  <span class="s">"Release escrow on Sepolia"</span>,
    <span class="k">"nodes"</span>: [ <span class="c">/* trigger + action nodes */</span> ],
    <span class="k">"edges"</span>: [ <span class="c">/* wiring */</span> ]
  },
  <span class="k">"workflowRef"</span>: <span class="s">"optional-label"</span>  <span class="c">// echoed back on the report</span>
}</pre>

<h2>Response</h2>
<pre>{
  <span class="k">"passed"</span>: <span class="n">false</span>,                  <span class="c">// false when any error-severity issue is found</span>
  <span class="k">"counts"</span>: { <span class="k">"error"</span>: <span class="n">4</span>, <span class="k">"warn"</span>: <span class="n">1</span>, <span class="k">"info"</span>: <span class="n">1</span> },
  <span class="k">"issues"</span>: [ {
    <span class="k">"trap"</span>:     <span class="s">"silently-ignored-integration-id"</span>,
    <span class="k">"severity"</span>: <span class="s">"error"</span>,
    <span class="k">"path"</span>:     <span class="s">"nodes[1].data.config.integrationId"</span>,
    <span class="k">"detail"</span>:   <span class="s">"…why this bites you…"</span>,
    <span class="k">"fix"</span>:      <span class="s">"…copy-pasteable correction…"</span>
  } ],
  <span class="k">"summary"</span>: <span class="s">"Audit failed: 4 errors…"</span>,
  <span class="k">"actionNodesScanned"</span>: <span class="n">1</span>,
  <span class="k">"workflowRef"</span>: <span class="s">"optional-label"</span>
}</pre>

<h2>Fields</h2>
<table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead><tbody>
<tr><td class="f">workflow</td><td class="t">object <span class="req">required</span></td>
<td class="d">A KeeperHub workflow definition. Paste it from <code>GET /api/workflows/{id}</code> or the editor's JSON view.</td></tr>
<tr><td class="f">workflowRef</td><td class="t">string</td>
<td class="d">Optional label echoed on the report. Useful when auditing many workflows.</td></tr>
<tr><td class="f">issues[].severity</td><td class="t">enum</td>
<td class="d"><code style="color:var(--blood)">error</code> mis-routes or fails at execute time ·
<code style="color:var(--yellow)">warn</code> accepted but non-canonical ·
<code style="color:var(--accent)">info</code> advisory.</td></tr>
<tr><td class="f">issues[].fix</td><td class="t">string</td>
<td class="d">A correction you can paste, not just a description of the problem.</td></tr>
<tr><td class="f">actionNodesScanned</td><td class="t">int</td>
<td class="d">How many <code>web3/write-contract</code> nodes were examined. <code>0</code> means nothing here is in scope.</td></tr>
</tbody></table>

<h2>cURL</h2>
<pre><span class="c"># paste straight into a terminal</span>
curl -sS -X POST https://kajota-hub.onrender.com/concierge/coach/audit-workflow \\
  -H <span class="s">'content-type: application/json'</span> \\
  -d <span class="s">'{"workflow":{"name":"probe","nodes":[{"id":"s","type":"action",
     "data":{"config":{"actionType":"web3/write-contract",
     "function":"release","integrationId":"int_x"}}}],"edges":[]}}'</span>

<span class="c"># this page, as JSON, for API clients</span>
curl -sS -H <span class="s">'accept: application/json'</span> \\
  https://kajota-hub.onrender.com/concierge/coach/audit-workflow</pre>

<footer>
<a href="https://kajota-hub.onrender.com/keeperhub#coach">Interactive console →</a>
<a href="https://github.com/KeeperHub/keeperhub/pull/1857" target="_blank">Merged bounty PR ↗</a>
<a href="https://github.com/KaJota-inc/kajota-coach" target="_blank">Source ↗</a>
<a href="/concierge/docs">OpenAPI ↗</a>
</footer>
</div>

<script>
const BAD = {workflow:{name:"buggy release",nodes:[
 {id:"t",type:"trigger",data:{label:"HTTP",config:{triggerType:"HTTP"}}},
 {id:"s",type:"action",data:{label:"release",config:{
   actionType:"web3/write-contract",network:11155111,integrationId:"int_your-keeper",
   contractAddress:"0x599869cef2e4c52e2c9074caaf8f9fb0cb191776",function:"release",
   abi:[{type:"function",name:"release"}],functionArgs:["{{@trigger.body.depositId}}"]}}}],
 edges:[]},workflowRef:"broken-example"};
const GOOD = {workflow:{name:"Release escrow on Sepolia",nodes:[
 {id:"trigger-1",type:"trigger",data:{label:"HTTP",config:{triggerType:"HTTP",httpMethod:"POST"}}},
 {id:"step-1",type:"action",data:{label:"Release Escrow",config:{
   actionType:"web3/write-contract",network:"11155111",web3Connection:"default",
   contractAddress:"0x599869cef2e4c52e2c9074caaf8f9fb0cb191776",abiFunction:"release",
   functionArgs:'["{{@trigger-1:HTTP.depositId}}"]',
   abi:'[{"type":"function","name":"release","stateMutability":"nonpayable","inputs":[{"name":"depositId","type":"bytes32"}],"outputs":[]}]'}}}],
 edges:[{id:"e",source:"trigger-1",target:"step-1"}]},workflowRef:"correct-example"};

const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const load=o=>{$("#in").value=JSON.stringify(o,null,2);$("#out").innerHTML="";};

$("#bad").onclick=()=>load(BAD);
$("#good").onclick=()=>load(GOOD);
load(BAD);

$("#run").onclick=async()=>{
  const b=$("#run"),out=$("#out");
  let payload;
  try{payload=JSON.parse($("#in").value);}
  catch(e){out.innerHTML='<div class="banner fail">JSON parse error: '+esc(e.message)+'</div>';return;}
  b.disabled=true;b.textContent="Sending…";
  const t0=performance.now();
  try{
    const r=await fetch(location.pathname,{method:"POST",
      headers:{"content-type":"application/json"},body:JSON.stringify(payload)});
    const ms=Math.round(performance.now()-t0);
    const j=await r.json();
    if(!r.ok){out.innerHTML='<div class="banner fail">HTTP '+r.status+' — '+esc(j.detail||"")+'</div>';return;}
    const c=j.counts||{};
    out.innerHTML='<div class="banner '+(j.passed?"pass":"fail")+'">'
      +(j.passed?"✓ PASSED":"✗ FAILED")+' · '+(c.error||0)+' errors · '+(c.warn||0)+' warnings · '
      +(c.info||0)+' info · HTTP '+r.status+' · '+ms+'ms</div>'
      +'<p class="hint">'+esc(j.summary||"")+'</p>'
      +(j.issues||[]).map(i=>'<div class="iss '+esc(i.severity)+'">'
        +'<div class="hd"><span>'+esc(i.severity)+' · '+esc(i.trap)+'</span><span style="color:var(--dim)">'+esc(i.path)+'</span></div>'
        +'<div>'+esc(i.detail)+'</div><div class="fix">→ '+esc(i.fix)+'</div></div>').join("");
  }catch(e){
    out.innerHTML='<div class="banner fail">request failed: '+esc(e.message)+'</div>';
  }finally{b.disabled=false;b.textContent="Send request";}
};
</script></body></html>"""


@app.get("/coach/audit-workflow")
async def coach_audit_workflow_info(request: Request):
    """Self-describing GET.

    Content-negotiated: a browser (Accept: text/html) gets a real page
    with schema, a paste-and-run curl, and a try-it form that POSTs back
    here. Anything else — curl, an agent, a script — gets the JSON
    descriptor unchanged, so this stays machine-readable.
    """
    if "text/html" in (request.headers.get("accept") or ""):
        return HTMLResponse(_AUDIT_PAGE)
    return JSONResponse({
        "endpoint": "/coach/audit-workflow",
        "method": "POST",
        "purpose": (
            "Static second-opinion audit of a KeeperHub `web3/write-contract` "
            "workflow. Catches every trap documented in the merged bounty PR "
            "KeeperHub/keeperhub#1857 (commit ee4b6a0) plus a couple of adjacent "
            "ones (silently-ignored integrationId vs canonical web3Connection, "
            "raw-array vs JSON-encoded-string functionArgs / abi, broken "
            "{{@trigger.body.x}} template pattern, numeric-vs-string network, "
            "missing HTTP body wrap). Purely diagnostic — nothing signs or writes."
        ),
        "requestBody": {
            "workflow": "KH workflow definition (name, nodes, edges) — required",
            "workflowRef": "optional label for the report",
        },
        "curlExample": (
            "curl -X POST https://kajota-hub.onrender.com/concierge/coach/audit-workflow "
            "-H 'content-type: application/json' "
            "-d '{\"workflow\":{\"name\":\"probe\",\"nodes\":[{\"id\":\"s\",\"type\":\"action\",\"data\":{\"config\":{\"actionType\":\"web3/write-contract\",\"function\":\"release\",\"integrationId\":\"int_x\"}}}],\"edges\":[]}}'"
        ),
        "interactiveDemo": "https://kajota-hub.onrender.com/keeperhub#coach",
        "sourceRepo": "https://github.com/KaJota-inc/kajota-coach",
        "sourceModule": "agent/kajota_concierge/coach_auditor.py",
        "bountyPR": "https://github.com/KeeperHub/keeperhub/pull/1857",
        "swaggerUi": "/concierge/docs",
        "htmlPage": "open this URL in a browser for the interactive version",
    })


class TriageRequest(BaseModel):
    """Body for POST /coach/triage — classify a free-text buyer message."""

    message: str
    preferLLM: bool = True


class TriageResponse(BaseModel):
    isDispute: bool
    severity: str
    category: str
    summary: str
    classifier: str
    confidence: float


@app.get("/coach/triage")
async def coach_triage_info() -> dict[str, Any]:
    """Self-describing GET so the URL is safe to share."""
    return {
        "endpoint": "/coach/triage",
        "method": "POST",
        "purpose": (
            "Classify a free-text buyer message as a dispute or not. This is "
            "the one judgement in Coach that a rules table cannot make — no "
            "keyword list reads English properly. The output feeds "
            "`activeDispute` on /coach/should-release, so a positive "
            "classification can HOLD or REJECT a release but can never cause "
            "one: the failure mode points at caution, not at loss."
        ),
        "requestBody": {
            "message": "the buyer's message, verbatim — required",
            "preferLLM": "bool, default true; false forces the keyword heuristic",
        },
        "curlExample": (
            "curl -X POST https://kajota-hub.onrender.com/concierge/coach/triage "
            "-H 'content-type: application/json' "
            "-d '{\"message\":\"box arrived but the seal was broken and two units are missing\"}'"
        ),
        "swaggerUi": "/concierge/docs",
    }


@app.post("/coach/triage", response_model=TriageResponse)
async def coach_triage(req: TriageRequest) -> TriageResponse:
    """LLM dispute triage — the judgement rules can't make.

    Deliberately the ONLY model-driven decision in the escrow path, and
    deliberately not a release decision. It emits a classification that a
    deterministic rule then consumes, which bounds the blast radius: a
    wrong "dispute" stalls a payout for a human to look at; a wrong "no
    dispute" merely declines to block, and every other hard rule still has
    to pass on its own.

    Falls back to a conservative keyword heuristic when Gemini is
    unavailable — biased toward flagging, since over-flagging costs a
    human glance and under-flagging costs the buyer their money.
    """
    result = await triage_message(req.message, prefer_llm=req.preferLLM)
    return TriageResponse(**result.to_dict())


@app.post("/coach/audit-workflow", response_model=AuditWorkflowResponse)
async def coach_audit_workflow(req: AuditWorkflowRequest) -> AuditWorkflowResponse:
    """Second-opinion audit of a KH `web3/write-contract` workflow.

    Runs the trap catalogue from KeeperHub/keeperhub#1857 (merged
    Aug 3 2026 as commit ee4b6a0) against the supplied workflow
    definition. Purely diagnostic — nothing signs or writes. Accepts
    the workflow inline via `workflow`; workflow-id fetch is deferred
    to the kajota-coach edition of this endpoint where a KH_API_KEY
    is provisioned.
    """
    report = audit_workflow(req.workflow, workflow_ref=req.workflowRef or "inline")
    return AuditWorkflowResponse(**report.to_dict())


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
