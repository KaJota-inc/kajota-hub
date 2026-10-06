"""Mandate commitment — Python mirror of MandateAnchor.mandateCommitment() in Solidity.

The on-chain contract computes:

    keccak256(
        abi.encode(
            mandateId,              bytes32
            bank,                   address
            idempotencyKey,         bytes32
            amount,                 uint64
            postedAt,               uint64
            deadline,               uint64
            envelopeHash,           bytes32
            sanctionsListVersion,   bytes32
            occurrence              uint8
        )
    )

Reproducing this off-chain lets a bank, a regulator, or a judge recompute the on-chain commitment
from the stored fields and compare it against the chain, without an RPC round-trip. The commitment
excludes the mutable `status` field by design — see package docstring.
"""

from __future__ import annotations

from dataclasses import dataclass

from eth_abi import encode
from eth_hash.auto import keccak


_SOLIDITY_TYPES = (
    "bytes32",   # mandateId
    "address",   # bank
    "bytes32",   # idempotencyKey
    "uint64",    # amount
    "uint64",    # postedAt
    "uint64",    # deadline
    "bytes32",   # envelopeHash
    "bytes32",   # sanctionsListVersion
    "uint8",     # occurrence
)


@dataclass(frozen=True, slots=True)
class Mandate:
    """A mandate row, exactly as the chain stores it (status omitted — not in the commitment)."""

    mandate_id: bytes          # 32 bytes
    bank: str                  # 0x-prefixed 20-byte hex address
    idempotency_key: bytes     # 32 bytes
    amount: int                # uint64, minor units
    posted_at: int             # uint64, seconds since epoch
    deadline: int              # uint64, seconds since epoch
    envelope_hash: bytes       # 32 bytes
    sanctions_list_version: bytes  # 32 bytes
    occurrence: int            # uint8


def mandate_commitment(m: Mandate) -> bytes:
    """Return the 32-byte keccak256 commitment matching Solidity's `mandateCommitment()`."""

    _check_bytes32(m.mandate_id, "mandate_id")
    _check_bytes32(m.idempotency_key, "idempotency_key")
    _check_bytes32(m.envelope_hash, "envelope_hash")
    _check_bytes32(m.sanctions_list_version, "sanctions_list_version")
    _check_uint(m.amount, 64, "amount")
    _check_uint(m.posted_at, 64, "posted_at")
    _check_uint(m.deadline, 64, "deadline")
    _check_uint(m.occurrence, 8, "occurrence")
    bank_bytes = _check_address(m.bank)

    values = (
        m.mandate_id,
        bank_bytes,
        m.idempotency_key,
        m.amount,
        m.posted_at,
        m.deadline,
        m.envelope_hash,
        m.sanctions_list_version,
        m.occurrence,
    )
    return keccak(encode(_SOLIDITY_TYPES, values))


def _check_bytes32(value: bytes, name: str) -> None:
    if not isinstance(value, (bytes, bytearray)) or len(value) != 32:
        raise ValueError(f"{name} must be exactly 32 bytes, got {len(value)}")


def _check_uint(value: int, bits: int, name: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    if value.bit_length() > bits:
        raise ValueError(f"{name} exceeds uint{bits} range")


def _check_address(value: str) -> str:
    """eth-abi accepts a 0x-prefixed hex address and left-pads it to 32 bytes on encode."""
    if not isinstance(value, str) or not value.startswith("0x") or len(value) != 42:
        raise ValueError(f"bank must be a 0x-prefixed 20-byte hex address, got {value!r}")
    try:
        int(value, 16)
    except ValueError as e:
        raise ValueError(f"bank is not valid hex: {value!r}") from e
    return value
