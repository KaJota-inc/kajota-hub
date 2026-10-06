"""Payflow Mandate Beacon — off-chain primitives for the on-chain Beacon rail.

Mirrors `contracts/beacon/MandateAnchor.sol` in `kajota-zama` on branch
`hackathon/bli-mandate-beacon`. The two primitives in this package are:

- `canonical_mandate(...)` — deterministic serialization of the mandate fields a bank will post.
  Fed into the idempotency key, where the server composes it with the amount and a Chainlink CRE
  tick bucket. Not for the on-chain commitment; the on-chain commitment uses abi.encode.

- `mandate_commitment(...)` — byte-for-byte reproduction of the Solidity view
  `MandateAnchor.mandateCommitment(bytes32)`. A bank, a regulator, or a judge can recompute the
  on-chain commitment from the stored fields and compare, no RPC round-trip required.

The commitment deliberately excludes the mutable `status` field so a settled or breached mandate
reads the same hash as the original posting — the status transition is its own on-chain event, not
a rewrite of the audit lineage.
"""

from payflow.mandate.commitment import mandate_commitment
from payflow.mandate.canonical import canonical_mandate, idempotency_key

__all__ = ["mandate_commitment", "canonical_mandate", "idempotency_key"]
