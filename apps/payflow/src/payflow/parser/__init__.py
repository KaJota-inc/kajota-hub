import json
from pathlib import Path

from payflow.models import Envelope
from payflow.parser.audit_trail import parse_audit_trail_json
from payflow.parser.nibss_json import parse_json
from payflow.parser.soap import parse_soap

__all__ = ["parse_audit_trail_json", "parse_file", "parse_json", "parse_soap"]


def parse_file(path: str | Path) -> Envelope:
    """Auto-detect envelope format and parse.

    - Starts with `<` → SOAP XML
    - Starts with `{` and has a `raw_request` key → Remita audit-trail row
    - Starts with `{` otherwise → REST JSON NIP envelope
    """
    text = Path(path).read_text()
    stripped = text.lstrip()
    if stripped.startswith("<"):
        return parse_soap(text)
    if stripped.startswith("{"):
        obj = json.loads(text)
        if any(k in obj for k in ("raw_request", "rawRequest")):
            return parse_audit_trail_json(text)
        return parse_json(text)
    raise ValueError(f"Cannot detect format for {path!r}: unexpected leading character")
