import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

from payflow.models import Envelope
from payflow.parser import parse_json, parse_soap

REQUEST_ALIASES = ("raw_request", "rawRequest", "request_body", "request_xml", "request", "req")
RESPONSE_ALIASES = ("raw_response", "rawResponse", "response_body", "response_xml", "response", "res")
METHOD_ALIASES = ("method", "operation", "transaction_type", "txn_type")
SESSION_ALIASES = ("session_id", "sessionId", "SessionID", "sessionid")
BANK_CODE_ALIASES = ("dest_bank_code", "destination_bank_code", "destinationInstitutionCode", "bank_code")


def _pick(headers: list[str], aliases: tuple[str, ...]) -> Optional[str]:
    lower_map = {h.lower(): h for h in headers}
    for alias in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    return None


def _parse_body(body: str) -> Envelope:
    stripped = body.lstrip()
    if stripped.startswith("<"):
        return parse_soap(body)
    if stripped.startswith("{"):
        return parse_json(body)
    raise ValueError(f"Cannot detect body format (leading char {stripped[:1]!r})")


def read_csv_envelopes(
    path: str | Path,
    *,
    request_column: Optional[str] = None,
    response_column: Optional[str] = None,
    method_column: Optional[str] = None,
    session_column: Optional[str] = None,
    bank_code_column: Optional[str] = None,
    limit: Optional[int] = None,
    skip_errors: bool = True,
) -> Iterator[Envelope]:
    """Stream envelopes from a bank's audit-trail CSV.

    Auto-detects the request/response/method/session/bank-code columns. Emits one
    Envelope per row. Response fields (response_code, response_message) win over
    request fields when merging.
    """
    with Path(path).open() as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        req_col = request_column or _pick(headers, REQUEST_ALIASES)
        res_col = response_column or _pick(headers, RESPONSE_ALIASES)
        method_col = method_column or _pick(headers, METHOD_ALIASES)
        session_col = session_column or _pick(headers, SESSION_ALIASES)
        bank_col = bank_code_column or _pick(headers, BANK_CODE_ALIASES)

        if not (req_col or res_col):
            raise ValueError(
                f"CSV has no request/response column. Headers: {headers}. "
                "Pass --request-column / --response-column to override."
            )

        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                return
            try:
                env = Envelope(source="audit_trail")
                req = (row.get(req_col) or "").strip() if req_col else ""
                res = (row.get(res_col) or "").strip() if res_col else ""

                if req:
                    parsed = _parse_body(req)
                    for f_ in ("session_id", "transaction_id", "method", "amount",
                               "source_account", "dest_account", "dest_bank_code", "narration"):
                        val = getattr(parsed, f_, None)
                        if val is not None:
                            setattr(env, f_, val)
                    env.raw_request = req

                if res:
                    parsed = _parse_body(res)
                    if parsed.response_code:
                        env.response_code = parsed.response_code
                    if parsed.response_message:
                        env.response_message = parsed.response_message
                    env.raw_response = res

                if method_col and (v := row.get(method_col)):
                    env.method = env.method or v.strip()
                if session_col and (v := row.get(session_col)):
                    env.session_id = env.session_id or v.strip()
                if bank_col and (v := row.get(bank_col)):
                    env.dest_bank_code = env.dest_bank_code or v.strip()

                yield env
            except Exception:
                if not skip_errors:
                    raise
                continue
