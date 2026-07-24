import hashlib
import hmac
import logging
import time
from typing import Optional

from payflow.integrations.freshdesk.client import FreshdeskClient
from payflow.integrations.freshdesk.config import FreshdeskConfig
from payflow.integrations.freshdesk.extract import extract_envelope_from_ticket
from payflow.integrations.freshdesk.format import format_triage_note
from payflow.integrations.freshdesk.observability import (
    incr,
    new_request_id,
    setup_json_logging,
    snapshot,
    uptime_seconds,
)
from payflow.kb import KB, load_kb
from payflow.triage import triage as _triage

logger = logging.getLogger("payflow.freshdesk")

_SIGNATURE_HEADER = "x-freshdesk-signature"
_INTERNAL_TOKEN_HEADER = "x-internal-token"


def verify_signature(body: bytes, signature: Optional[str], secret: str) -> bool:
    """HMAC-SHA256 hex-digest comparison, constant-time. Empty signature → False."""
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def build_app(
    config: Optional[FreshdeskConfig] = None,
    kb: Optional[KB] = None,
    client: Optional[FreshdeskClient] = None,
    configure_logging: bool = False,
):
    """Build the FastAPI app.

    - `client=None` + `config.dry_run=True` → no writeback.
    - `configure_logging=True` at boot (in the ASGI entrypoint) installs the JSON formatter.
      Tests leave it False so pytest's log capture keeps working.
    """
    try:
        from fastapi import FastAPI, HTTPException, Request
    except ImportError as e:
        raise ImportError(
            "FastAPI required for webhook server. Install with: uv sync --extra webhook"
        ) from e

    config = config or FreshdeskConfig.from_env()
    kb = kb or load_kb()
    if client is None and not config.dry_run:
        client = FreshdeskClient(config)

    if configure_logging:
        setup_json_logging(config.log_level)

    app = FastAPI(title="Payflow — Freshdesk webhook", version="0.1")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "dry_run": config.dry_run, "uptime_s": round(uptime_seconds(), 1)}

    @app.get("/internal/metrics")
    def metrics(request: Request) -> dict:
        _require_internal_token(request, config.internal_token)
        return {"counters": snapshot(), "uptime_s": round(uptime_seconds(), 1)}

    @app.post("/webhook/freshdesk")
    async def webhook(request: Request) -> dict:
        started = time.perf_counter()
        request_id = new_request_id()
        incr("webhook_received_total")

        raw = await request.body()
        sig = request.headers.get(_SIGNATURE_HEADER)
        if not verify_signature(raw, sig, config.webhook_secret):
            incr("webhook_signature_rejected_total")
            logger.warning("signature_rejected", extra={"request_id": request_id})
            raise HTTPException(status_code=401, detail="Invalid or missing signature")

        try:
            payload = await request.json()
        except Exception as e:
            incr("webhook_bad_json_total")
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

        ticket = payload.get("freshdesk_webhook") or payload
        ticket_id = ticket.get("ticket_id") or ticket.get("id")
        if not ticket_id:
            incr("webhook_missing_ticket_id_total")
            raise HTTPException(status_code=400, detail="No ticket_id in payload")

        envelope = extract_envelope_from_ticket(ticket, default_dialect=config.default_dialect)
        if envelope is None:
            incr("ticket_extract_failed_total")
            logger.info("no_envelope", extra={"request_id": request_id, "ticket_id": ticket_id})
            return {"status": "skipped", "reason": "no envelope in ticket body", "ticket_id": ticket_id}

        result = _triage(envelope, kb, use_llm=config.use_llm, verify=config.verify)
        note = format_triage_note(result)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        incr(
            "ticket_triaged_total",
            retry_strategy=result.retry_strategy.value,
            confidence=result.confidence,
        )

        log_extra = {
            "request_id": request_id,
            "ticket_id": ticket_id,
            "dialect": envelope.dialect.value if envelope.dialect else None,
            "method": envelope.method,
            "response_code": envelope.response_code,
            "retry_strategy": result.retry_strategy.value,
            "confidence": result.confidence,
            "duration_ms": duration_ms,
            "dry_run": config.dry_run,
        }
        logger.info("triaged", extra=log_extra)

        if config.dry_run or client is None:
            incr("ticket_dry_run_total")
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
            client.post_private_note(ticket_id, note)
            incr("freshdesk_note_posted_total")
        except Exception as e:
            incr("freshdesk_note_failed_total")
            logger.exception("note_post_failed", extra={"request_id": request_id, "ticket_id": ticket_id})
            raise HTTPException(status_code=502, detail=f"Freshdesk note POST failed: {e}")

        try:
            client.add_tags(
                ticket_id,
                [f"payflow:{result.retry_strategy.value}", f"payflow-confidence:{result.confidence}"],
            )
            incr("freshdesk_tags_updated_total")
        except Exception as e:
            incr("freshdesk_tags_failed_total")
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
        return  # dev mode — endpoints open
    provided = request.headers.get(_INTERNAL_TOKEN_HEADER) or request.headers.get(
        _INTERNAL_TOKEN_HEADER.title()
    )
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="internal token required")
