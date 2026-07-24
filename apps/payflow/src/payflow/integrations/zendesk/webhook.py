import base64
import hashlib
import hmac
import logging
import time
from typing import Optional

from payflow.integrations._shared.extract import extract_envelope_from_ticket
from payflow.integrations._shared.format import format_triage_note
from payflow.integrations._shared.observability import (
    incr,
    new_request_id,
    setup_json_logging,
    snapshot,
    uptime_seconds,
)
from payflow.integrations.zendesk.client import ZendeskClient
from payflow.integrations.zendesk.config import ZendeskConfig
from payflow.kb import KB, load_kb
from payflow.triage import triage as _triage

logger = logging.getLogger("payflow.zendesk")

_SIGNATURE_HEADER = "x-zendesk-webhook-signature"
_TIMESTAMP_HEADER = "x-zendesk-webhook-signature-timestamp"
_INTERNAL_TOKEN_HEADER = "x-internal-token"


def verify_signature(
    body: bytes,
    timestamp: Optional[str],
    signature: Optional[str],
    secret: str,
) -> bool:
    """Zendesk webhook signature verification.

    Signature = base64(HMAC-SHA256(f"{timestamp}{body_utf8}", secret)).
    Must include both the timestamp header and the signature header; either missing → False.
    Constant-time comparison against base64-decoded expected digest.
    """
    if not signature or not timestamp:
        return False
    message = timestamp.encode() + body
    expected_bytes = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected_bytes).decode()
    return hmac.compare_digest(expected_b64, signature)


def build_app(
    config: Optional[ZendeskConfig] = None,
    kb: Optional[KB] = None,
    client: Optional[ZendeskClient] = None,
    configure_logging: bool = False,
):
    """Build the Zendesk webhook FastAPI app.

    Mirrors `freshdesk.webhook.build_app` — shared extract/format/observability keep
    behaviour identical across vendors. Differences are auth, signature scheme, and
    the comment/tag endpoint shapes handled by ZendeskClient.
    """
    try:
        from fastapi import FastAPI, HTTPException, Request
    except ImportError as e:
        raise ImportError(
            "FastAPI required for webhook server. Install with: uv sync --extra webhook"
        ) from e

    config = config or ZendeskConfig.from_env()
    kb = kb or load_kb()
    if client is None and not config.dry_run:
        client = ZendeskClient(config)

    if configure_logging:
        setup_json_logging(config.log_level)

    app = FastAPI(title="Payflow — Zendesk webhook", version="0.1")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "dry_run": config.dry_run, "uptime_s": round(uptime_seconds(), 1)}

    @app.get("/internal/metrics")
    def metrics(request: Request) -> dict:
        _require_internal_token(request, config.internal_token)
        return {"counters": snapshot(), "uptime_s": round(uptime_seconds(), 1)}

    @app.post("/webhook/zendesk")
    async def webhook(request: Request) -> dict:
        started = time.perf_counter()
        request_id = new_request_id()
        incr("webhook_received_total", integration="zendesk")

        raw = await request.body()
        sig = request.headers.get(_SIGNATURE_HEADER)
        ts = request.headers.get(_TIMESTAMP_HEADER)
        if not verify_signature(raw, ts, sig, config.webhook_secret):
            incr("webhook_signature_rejected_total", integration="zendesk")
            logger.warning("signature_rejected", extra={"request_id": request_id, "integration": "zendesk"})
            raise HTTPException(status_code=401, detail="Invalid or missing signature")

        try:
            payload = await request.json()
        except Exception as e:
            incr("webhook_bad_json_total", integration="zendesk")
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

        # Zendesk webhooks commonly wrap under `ticket`; the extract helper also unwraps.
        ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else payload
        ticket_id = ticket.get("id") or ticket.get("ticket_id")
        if not ticket_id:
            incr("webhook_missing_ticket_id_total", integration="zendesk")
            raise HTTPException(status_code=400, detail="No ticket id in payload")

        envelope = extract_envelope_from_ticket(ticket, default_dialect=config.default_dialect)
        if envelope is None:
            incr("ticket_extract_failed_total", integration="zendesk")
            logger.info("no_envelope", extra={"request_id": request_id, "ticket_id": ticket_id, "integration": "zendesk"})
            return {"status": "skipped", "reason": "no envelope in ticket body", "ticket_id": ticket_id}

        result = _triage(envelope, kb, use_llm=config.use_llm, verify=config.verify)
        note = format_triage_note(result)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        incr(
            "ticket_triaged_total",
            integration="zendesk",
            retry_strategy=result.retry_strategy.value,
            confidence=result.confidence,
        )
        logger.info("triaged", extra={
            "request_id": request_id, "ticket_id": ticket_id, "integration": "zendesk",
            "dialect": envelope.dialect.value if envelope.dialect else None,
            "method": envelope.method, "response_code": envelope.response_code,
            "retry_strategy": result.retry_strategy.value, "confidence": result.confidence,
            "duration_ms": duration_ms, "dry_run": config.dry_run,
        })

        if config.dry_run or client is None:
            incr("ticket_dry_run_total", integration="zendesk")
            return {
                "status": "dry_run",
                "ticket_id": ticket_id,
                "retry_strategy": result.retry_strategy.value,
                "confidence": result.confidence,
                "note_preview": note,
                "duration_ms": duration_ms,
                "request_id": request_id,
            }

        try:
            client.post_internal_comment(ticket_id, note)
            incr("zendesk_comment_posted_total")
        except Exception as e:
            incr("zendesk_comment_failed_total")
            logger.exception("comment_post_failed", extra={"request_id": request_id, "ticket_id": ticket_id})
            raise HTTPException(status_code=502, detail=f"Zendesk comment PUT failed: {e}")

        try:
            client.add_tags(
                ticket_id,
                [f"payflow:{result.retry_strategy.value}", f"payflow-confidence:{result.confidence}"],
            )
            incr("zendesk_tags_updated_total")
        except Exception as e:
            incr("zendesk_tags_failed_total")
            logger.warning("tag_update_failed", extra={
                "request_id": request_id, "ticket_id": ticket_id, "error": str(e),
            })

        return {
            "status": "triaged",
            "ticket_id": ticket_id,
            "retry_strategy": result.retry_strategy.value,
            "confidence": result.confidence,
            "duration_ms": duration_ms,
            "request_id": request_id,
        }

    return app


def _require_internal_token(request, expected: Optional[str]) -> None:
    from fastapi import HTTPException
    if expected is None:
        return  # dev mode
    provided = request.headers.get(_INTERNAL_TOKEN_HEADER) or request.headers.get(
        _INTERNAL_TOKEN_HEADER.title()
    )
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="internal token required")
