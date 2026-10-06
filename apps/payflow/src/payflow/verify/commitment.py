import hashlib
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from payflow.models import TriageResult

# Schema version — bump when the commitment structure changes so parties can
# tell when they're committing/verifying under incompatible rules.
COMMITMENT_SCHEMA_VERSION = 1


class CommitmentSchema(BaseModel):
    """The canonical structure hashed into a commitment.

    Deliberately narrow: fields with PII (narration, response_message text,
    account numbers) are either hashed or omitted. The verdict side is included
    verbatim because the whole point is to prove *what verdict was reached*.
    """
    v: int = Field(COMMITMENT_SCHEMA_VERSION, description="Schema version.")
    ts: Optional[str] = Field(None, description="RFC3339 timestamp (set by submitter).")
    envelope: dict = Field(..., description="Non-PII envelope fingerprint.")
    verdict: dict = Field(..., description="Triage verdict (cause, strategy, confidence).")
    evidence_hash: str = Field(..., description="SHA-256 over the sorted, joined evidence lines.")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_text(s: Optional[str]) -> Optional[str]:
    """Hash sensitive free-text (narration, response_message) so the commitment
    is reconstructible from a redacted envelope but reveals no raw content.
    """
    if s is None:
        return None
    return _sha256_hex(s.encode("utf-8"))


def _hash_evidence(evidence: list[str]) -> str:
    """Order-sensitive hash of evidence lines (order carries meaning — it's the
    order the model cited them in). Separator is `\\n` so lines can't collide."""
    joined = "\n".join(evidence)
    return _sha256_hex(joined.encode("utf-8"))


def build_commitment(
    result: TriageResult,
    *,
    ts: Optional[str] = None,
) -> CommitmentSchema:
    """Build the canonical commitment structure for a triage result.

    No raw PII reaches the commitment. The verdict is included verbatim because
    the commitment's whole purpose is to pin down *what Payflow decided*.
    """
    env = result.envelope

    envelope_fingerprint = {
        "dialect": env.dialect.value if env.dialect else None,
        "method": env.method,
        "response_code": env.response_code,
        "response_message_hash": _hash_text(env.response_message),
        "session_id_hash": _hash_text(env.session_id),
        "amount": env.amount,  # amounts are not PII, keep them visible
        "source": env.source,
    }
    verdict = {
        "cause": result.cause,
        "action": result.action,
        "retry_strategy": result.retry_strategy.value,
        "retryable": result.retryable,
        "confidence": result.confidence,
    }
    return CommitmentSchema(
        v=COMMITMENT_SCHEMA_VERSION,
        ts=ts,
        envelope=envelope_fingerprint,
        verdict=verdict,
        evidence_hash=_hash_evidence(result.evidence),
    )


def _canonical_json(obj: Any) -> bytes:
    """JSON encoding chosen so two parties can converge on identical bytes:
    - sort_keys for deterministic ordering
    - compact separators (no whitespace)
    - UTF-8 bytes
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def commitment_hash(commitment: CommitmentSchema) -> str:
    """SHA-256 hex digest of the canonically-encoded commitment."""
    return _sha256_hex(_canonical_json(commitment.model_dump()))


def commitment_bytes32(commitment: CommitmentSchema) -> bytes:
    """32-byte big-endian commitment hash, ready for an EVM `bytes32` argument."""
    hex_digest = commitment_hash(commitment)
    return bytes.fromhex(hex_digest)
