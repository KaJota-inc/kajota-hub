"""Canonical mandate serialization + idempotency-key composition.

The `idempotencyKey` the bank posts to `MandateAnchor.sol` is server-derived from the request
itself, so an agent cannot forge a key that collides-but-passes. The composition is:

    idempotencyKey = sha256(canonical_mandate ‖ amount_be8 ‖ cre_tick_bucket_be8)

Where:
- `canonical_mandate` is a deterministic byte sequence over the mandate request's audit fields.
  JSON Canonicalization Scheme (RFC 8785) is the stable reference, but we only need a subset — the
  mandate request shape is a flat dict of ASCII keys to primitive values (strings, ints, bools),
  which lets us serialize deterministically without the full RFC 8785 corner cases around numbers
  and nested structures.
- `amount_be8` is the 8-byte big-endian representation of the amount in minor units.
- `cre_tick_bucket_be8` is the 8-byte big-endian 5-minute bucket index — epoch_seconds // 300.
  This gives a server-authored time partition that an attacker's replay cannot forge, and that a
  CRE workflow can reproduce exactly five minutes later.

The result is 32 bytes, suitable as the `idempotencyKey` input to `postMandate`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Mapping


FIVE_MIN_SECONDS = 300


def canonical_mandate(fields: Mapping[str, object]) -> bytes:
    """Deterministic JSON serialization of a flat mandate-request dict.

    Keys are sorted; separators are the compact `",":","` pair; strings are escaped per JSON.
    This is enough for a mandate request whose fields are all strings, ints, bools, or null.
    """

    _check_flat(fields)
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def idempotency_key(
    canonical: bytes,
    amount: int,
    cre_tick_bucket: int,
) -> bytes:
    """Compose the 32-byte idempotency key the chain stores."""

    if not isinstance(canonical, (bytes, bytearray)):
        raise TypeError("canonical must be bytes (from canonical_mandate())")
    if not isinstance(amount, int) or amount < 0 or amount.bit_length() > 64:
        raise ValueError("amount must be a non-negative uint64")
    if not isinstance(cre_tick_bucket, int) or cre_tick_bucket < 0 or cre_tick_bucket.bit_length() > 64:
        raise ValueError("cre_tick_bucket must be a non-negative uint64")

    h = hashlib.sha256()
    h.update(bytes(canonical))
    h.update(amount.to_bytes(8, "big"))
    h.update(cre_tick_bucket.to_bytes(8, "big"))
    return h.digest()


def cre_tick_bucket_for(epoch_seconds: int) -> int:
    """Return the 5-minute bucket index covering `epoch_seconds` — matches the CRE workflow."""
    if epoch_seconds < 0:
        raise ValueError("epoch_seconds must be non-negative")
    return epoch_seconds // FIVE_MIN_SECONDS


def _check_flat(fields: Mapping[str, object]) -> None:
    for key, value in fields.items():
        if not isinstance(key, str):
            raise TypeError(f"canonical_mandate requires string keys; got {key!r}")
        if not isinstance(value, (str, int, bool, type(None))):
            raise TypeError(
                f"canonical_mandate requires primitive values; "
                f"got {type(value).__name__} for key {key!r}",
            )
