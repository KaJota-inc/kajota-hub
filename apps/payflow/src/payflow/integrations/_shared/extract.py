import re
from typing import Optional

from payflow.models import Dialect, Envelope
from payflow.parser import parse_json, parse_soap

_CODE_BLOCK_RE = re.compile(r"```(?:xml|json|soap)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_PRE_BLOCK_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL | re.IGNORECASE)
_XML_ENVELOPE_RE = re.compile(r"<[^>]*Envelope\b[^>]*>.*?</[^>]*Envelope>", re.DOTALL | re.IGNORECASE)
_JSON_OBJ_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
_DIALECT_TAG_RE = re.compile(r"^dialect:([a-z]+)$", re.IGNORECASE)

# Whitelist of HTML tags to strip. We do NOT strip `<[^>]+>` blindly — that would
# eat SOAP/XML tags like `<soap:Envelope>`. Anything not on this list survives.
_HTML_TAG_NAMES = (
    "p", "div", "span", "br", "hr",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "td", "th",
    "strong", "em", "b", "i", "u", "s",
    "a", "img",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "code",
)
_HTML_TAG_RE = re.compile(
    r"</?(?:" + "|".join(_HTML_TAG_NAMES) + r")\b[^>]*>",
    re.IGNORECASE,
)


def extract_dialect_from_tags(tags: Optional[list[str]]) -> Optional[Dialect]:
    """Look for a `dialect:xxx` tag. Returns the first matched Dialect, or None."""
    for tag in tags or []:
        m = _DIALECT_TAG_RE.match((tag or "").strip())
        if m:
            try:
                return Dialect(m.group(1).lower())
            except ValueError:
                continue
    return None


def extract_envelope_from_ticket(
    ticket: dict,
    default_dialect: Dialect = Dialect.CORE,
) -> Optional[Envelope]:
    """Locate and parse a NIP envelope in a helpdesk ticket payload.

    Ops teams paste envelopes in wildly different shapes. This tries, in order,
    across both the raw and HTML-entity-decoded description:
      1. Fenced ```xml / ```json / ``` blocks
      2. `<pre>...</pre>` blocks
      3. Bare `<*Envelope>...</*Envelope>` XML inline in HTML
      4. Bare `{...}` JSON that looks like a NIP envelope

    Also unwraps Zendesk-style `{"ticket": {...}}` wrapping before extracting.

    Dialect resolution: a `dialect:xxx` ticket tag → `default_dialect`.
    Only returns an envelope with a `response_code` or `session_id` — otherwise
    a random `{}` in the ticket body would false-positive.
    """
    ticket = ticket.get("ticket", ticket) if isinstance(ticket.get("ticket"), dict) else ticket
    description = (
        ticket.get("description_text")
        or ticket.get("description")
        or ticket.get("ticket_description")
        or ""
    )
    tags = ticket.get("tags") or ticket.get("ticket_tags") or []
    if not description:
        return None

    decoded = _decode_entities(description)
    text_only = _strip_known_html(decoded)

    for candidate in _collect_candidates(description, decoded, text_only):
        env = _try_parse(candidate)
        if env is not None and (env.response_code or env.session_id):
            env.dialect = extract_dialect_from_tags(tags) or default_dialect
            return env
    return None


def _collect_candidates(raw: str, decoded: str, text: str):
    """Yield candidate envelope strings in priority order across the three views."""
    for source in (raw, decoded):
        for m in _CODE_BLOCK_RE.finditer(source):
            yield m.group(1)
        for m in _PRE_BLOCK_RE.finditer(source):
            yield _strip_known_html(_decode_entities(m.group(1)))
        for m in _XML_ENVELOPE_RE.finditer(source):
            yield m.group()
    for m in _XML_ENVELOPE_RE.finditer(text):
        yield m.group()
    for m in _JSON_OBJ_RE.finditer(text):
        yield m.group()


def _strip_known_html(s: str) -> str:
    return _HTML_TAG_RE.sub(" ", s)


def _decode_entities(s: str) -> str:
    return (
        s.replace("&lt;", "<").replace("&gt;", ">")
        .replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    )


def _try_parse(content: str) -> Optional[Envelope]:
    if not content:
        return None
    content = content.strip()
    if not content:
        return None
    try:
        if content.startswith("<"):
            return parse_soap(content)
        if content.startswith("{"):
            return parse_json(content)
    except Exception:
        return None
    return None
