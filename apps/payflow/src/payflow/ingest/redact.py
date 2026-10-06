import hashlib
import os
import re

# NUBAN accounts are 10 digits; BVN and NG mobile numbers are 11 digits.
_ACCOUNT_RE = re.compile(r"\b\d{10}\b")
_ELEVEN_DIGIT_RE = re.compile(r"\b\d{11}\b")

_NARRATION_TAGS = ("NarrationTruncated", "Narration", "narrationTruncated", "narration")
_NARRATION_JSON_RE = re.compile(
    r'"(narration|Narration|narrationTruncated|NarrationTruncated)"\s*:\s*"([^"]*)"'
)


class Redactor:
    """Deterministic PII redaction for real-pilot ingest.

    Uses HMAC-BLAKE2b with a per-bank salt. Same input → same masked output so
    joins/dedup by account still work; the mapping is reversible only by the
    party holding the salt (typically the bank itself).

    Salt precedence: explicit `salt` argument → `PAYFLOW_REDACTION_SALT` env var →
    raises. We refuse to silently no-op on real data.
    """

    def __init__(self, salt: bytes | str | None = None):
        if salt is None:
            env_salt = os.environ.get("PAYFLOW_REDACTION_SALT")
            if not env_salt:
                raise RuntimeError(
                    "PAYFLOW_REDACTION_SALT env var required for real-data ingest. "
                    "Set a per-bank random salt (bank-held) so redaction is reversible only by them."
                )
            salt = env_salt
        self._salt = salt.encode() if isinstance(salt, str) else salt

    def _mac(self, s: str, prefix: str, digest_size: int = 6) -> str:
        h = hashlib.blake2b(s.encode(), key=self._salt, digest_size=digest_size).hexdigest()
        return f"{prefix}_{h}"

    def account(self, account: str) -> str:
        if not account or not account.strip():
            return account
        return self._mac(account.strip(), "RED")

    def bvn(self, bvn: str) -> str:
        if not bvn or not bvn.strip():
            return bvn
        return self._mac(bvn.strip(), "BVN")

    def phone(self, phone: str) -> str:
        if not phone or not phone.strip():
            return phone
        return self._mac(phone.strip(), "PHN", digest_size=5)

    def envelope_content(self, content: str) -> str:
        """Redact PII in raw envelope content (XML or JSON).

        Order matters: 11-digit patterns first (BVN/phone), then 10-digit (NUBAN),
        then narration tags/keys. Word-boundary anchors prevent overlap.
        """
        if not content:
            return content

        # 11-digit patterns look like BVN or NG mobile — both are PII, redact identically.
        content = _ELEVEN_DIGIT_RE.sub(lambda m: self._mac(m.group(), "ID11"), content)
        content = _ACCOUNT_RE.sub(lambda m: self._mac(m.group(), "RED"), content)

        for tag in _NARRATION_TAGS:
            open_close = re.compile(f"(<{tag}>)([^<]*)(</{tag}>)")
            content = open_close.sub(lambda m: f"{m.group(1)}[REDACTED]{m.group(3)}", content)

        content = _NARRATION_JSON_RE.sub(lambda m: f'"{m.group(1)}": "[REDACTED]"', content)
        return content
