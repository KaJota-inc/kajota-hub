import json
from typing import Any

from payflow.models import Envelope
from payflow.parser.soap import parse_soap

_REQ_KEYS = ("raw_request", "rawRequest")
_RES_KEYS = ("raw_response", "rawResponse")


def _first(obj: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return None


def parse_audit_trail_json(text: str) -> Envelope:
    """Parse a Remita `RequestAuditTrail` row (JSON) into an Envelope.

    The row's `raw_request` / `raw_response` LOBs hold the SOAP payloads; we
    parse those and merge into one Envelope with response fields winning.
    """
    row = json.loads(text)
    env = Envelope(source="audit_trail")

    raw_req = _first(row, *_REQ_KEYS)
    raw_res = _first(row, *_RES_KEYS)

    if raw_req:
        req = parse_soap(raw_req)
        for f in ("session_id", "transaction_id", "method", "amount",
                  "source_account", "dest_account", "dest_bank_code", "narration"):
            val = getattr(req, f, None)
            if val is not None:
                setattr(env, f, val)
        env.raw_request = raw_req

    if raw_res:
        res = parse_soap(raw_res)
        if res.response_code:
            env.response_code = res.response_code
        if res.response_message:
            env.response_message = res.response_message
        env.raw_response = raw_res

    env.method = env.method or _first(row, "method")
    env.session_id = env.session_id or _first(row, "session_id", "sessionId")
    env.transaction_id = env.transaction_id or _first(row, "transaction_id", "transactionId")
    return env
