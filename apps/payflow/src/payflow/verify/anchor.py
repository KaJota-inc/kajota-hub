from typing import Any, Optional

from pydantic import BaseModel

from payflow.verify.commitment import (
    CommitmentSchema,
    commitment_bytes32,
    commitment_hash,
)
from payflow.verify.config import AnchorConfig


class AnchorReceipt(BaseModel):
    """Outcome of an anchor submission (or dry-run simulation)."""
    commitment_hash: str
    contract_address: str
    chain_id: int
    function_name: str
    call_data: str
    submitted: bool
    tx_hash: Optional[str] = None
    dry_run: bool
    note: Optional[str] = None


def _function_selector(function_name: str) -> bytes:
    """Keccak-256 of `function_name(bytes32)` → first 4 bytes.

    Prefer `eth_hash` (keccak) when available (installed via the `beacon` extra);
    fall back to pycryptodome's keccak if `eth_hash` is absent.
    """
    sig = f"{function_name}(bytes32)".encode("ascii")
    try:
        from eth_hash.auto import keccak  # type: ignore
    except ImportError:
        try:
            from Crypto.Hash import keccak as _keccak  # type: ignore
            k = _keccak.new(digest_bits=256)
            k.update(sig)
            return k.digest()[:4]
        except ImportError as e:
            raise ImportError(
                "keccak backend missing. Install one via: "
                "`uv sync --extra beacon` (eth-hash[pycryptodome])."
            ) from e
    return keccak(sig)[:4]


class WitnessAnchorClient:
    """Submit a commitment hash to an EVM anchor contract.

    Lives behind an interface so tests can inject a stub. Real submission uses
    `web3.py` (optional dep); dry-run uses no external deps and returns a receipt
    with the pre-computed call data for inspection.
    """

    def __init__(
        self,
        config: AnchorConfig,
        web3_client: Any = None,
    ):
        self.config = config
        self._web3 = web3_client  # None → lazy import at submit time

    def submit(self, commitment: CommitmentSchema) -> AnchorReceipt:
        hash_hex = commitment_hash(commitment)
        hash_bytes = commitment_bytes32(commitment)
        selector = _function_selector(self.config.function_name)
        call_data = (selector + hash_bytes).hex()

        if self.config.dry_run:
            return AnchorReceipt(
                commitment_hash=hash_hex,
                contract_address=self.config.contract_address,
                chain_id=self.config.chain_id,
                function_name=self.config.function_name,
                call_data=f"0x{call_data}",
                submitted=False,
                dry_run=True,
                note="dry-run: commitment computed, no broadcast",
            )

        if self.config.private_key is None:
            raise ValueError(
                "Non-dry-run submission requires a private key. "
                "Set PAYFLOW_ANCHOR_PRIVATE_KEY or pass dry_run=True."
            )

        w3 = self._web3 if self._web3 is not None else _default_web3(self.config.rpc_url)
        tx = {
            "to": self.config.contract_address,
            "data": "0x" + call_data,
            "gas": self.config.gas_limit,
            "chainId": self.config.chain_id,
            "nonce": w3.eth.get_transaction_count(w3.eth.account.from_key(self.config.private_key).address),
            "gasPrice": w3.eth.gas_price,
            "value": 0,
        }
        signed = w3.eth.account.sign_transaction(tx, self.config.private_key)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        tx_hash = w3.eth.send_raw_transaction(raw)
        return AnchorReceipt(
            commitment_hash=hash_hex,
            contract_address=self.config.contract_address,
            chain_id=self.config.chain_id,
            function_name=self.config.function_name,
            call_data=f"0x{call_data}",
            submitted=True,
            tx_hash=tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash),
            dry_run=False,
        )


def _default_web3(rpc_url: str) -> Any:
    try:
        from web3 import Web3
    except ImportError as e:
        raise ImportError(
            "web3 required for live anchor submission. "
            "Install with: uv sync --extra web3"
        ) from e
    return Web3(Web3.HTTPProvider(rpc_url))
