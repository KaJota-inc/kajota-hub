"""Cross-institution evidence anchoring — Primitive 3 (Web3 extension).

Where the in-process `LLMVerifier` guarantees per-triage grounding, this module
produces an auditable, privacy-preserving commitment to the (envelope, verdict,
evidence) tuple and optionally anchors it on-chain. Three load-bearing properties:

- **Deterministic**: canonical JSON encoding + SHA-256 means two parties with
  the same source material converge on byte-identical hashes.
- **Privacy-preserving**: PII (narration, response_message free text) is hashed,
  not stored. Account numbers and session IDs are hashed with per-bank salt.
- **Replay-safe cross-institution**: once anchored to a public ledger, no party
  can retroactively claim a different verdict was observed at time T.

The on-chain anchor contract is intentionally pluggable — Payflow ships only
the Python side. See `AnchorConfig` for the contract interface it expects.
"""
from payflow.verify.anchor import AnchorReceipt, WitnessAnchorClient
from payflow.verify.commitment import (
    CommitmentSchema,
    build_commitment,
    commitment_bytes32,
    commitment_hash,
)
from payflow.verify.config import AnchorConfig

__all__ = [
    "AnchorConfig",
    "AnchorReceipt",
    "CommitmentSchema",
    "WitnessAnchorClient",
    "build_commitment",
    "commitment_bytes32",
    "commitment_hash",
]
