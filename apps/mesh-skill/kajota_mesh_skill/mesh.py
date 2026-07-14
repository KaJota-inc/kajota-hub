"""Web3 client wrapper around the deployed Sepolia CosellEscrow + CosellRegistry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from kajota_mesh_skill.settings import Settings


def _load_abi(name: str) -> list[dict[str, Any]]:
    """Load a contract ABI from the ``skill/abis/`` directory bundled with the package."""
    abi_dir = Path(__file__).resolve().parents[1] / "abis"
    with (abi_dir / f"{name}.json").open() as f:
        artifact = json.load(f)
    return artifact["abi"]


@dataclass
class DepositView:
    """Plain-data projection of an on-chain deposit record."""

    deposit_id: str
    listing_id: str
    buyer: str
    seller: str
    gross_amount: int
    fee_amount: int
    net_amount: int
    status: str  # "pending" | "released" | "refunded"


_STATUS_BY_INDEX = {0: "pending", 1: "released", 2: "refunded"}


class MeshClient:
    """Thin wrapper exposing only the operations the skill service needs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._w3: Web3 | None = None
        self._escrow: Any = None
        self._registry: Any = None
        self._account: Any = None
        if settings.is_live:
            self._connect()

    def _connect(self) -> None:
        s = self._settings
        w3 = Web3(Web3.HTTPProvider(s.rpc_url))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self._account = w3.eth.account.from_key(s.release_auth_key)
        w3.eth.default_account = self._account.address
        self._escrow = w3.eth.contract(
            address=Web3.to_checksum_address(s.escrow_address),
            abi=_load_abi("CosellEscrow"),
        )
        self._registry = w3.eth.contract(
            address=Web3.to_checksum_address(s.registry_address),
            abi=_load_abi("CosellRegistry"),
        )
        self._w3 = w3

    @property
    def live(self) -> bool:
        return self._w3 is not None

    @property
    def service_address(self) -> str:
        if self._account is None:
            return "0x" + "0" * 40
        return str(self._account.address)

    def get_deposit(self, deposit_id: str) -> DepositView | None:
        """Read a deposit by id from chain.  Returns ``None`` when dry-run."""
        if not self.live:
            return None
        deposit_bytes = bytes.fromhex(deposit_id.removeprefix("0x"))
        try:
            data = self._escrow.functions.getDeposit(deposit_bytes).call()
        except Exception:
            return None
        listing_id, buyer, seller, gross, fee, net, status_idx = data
        return DepositView(
            deposit_id=deposit_id,
            listing_id="0x" + listing_id.hex(),
            buyer=buyer,
            seller=seller,
            gross_amount=int(gross),
            fee_amount=int(fee),
            net_amount=int(net),
            status=_STATUS_BY_INDEX.get(int(status_idx), "unknown"),
        )

    def release(self, deposit_id: str) -> str:
        """Call ``release(depositId)`` and return the transaction hash.

        Returns a synthetic ``0xdry-...`` hash when ``MESH_DRY_RUN=true``.
        """
        if not self.live:
            return f"0xdry-release-{deposit_id[:16]}"
        deposit_bytes = bytes.fromhex(deposit_id.removeprefix("0x"))
        tx = self._escrow.functions.release(deposit_bytes).build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "chainId": self._settings.chain_id,
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def refund(self, deposit_id: str) -> str:
        """Call ``refund(depositId)`` and return the transaction hash."""
        if not self.live:
            return f"0xdry-refund-{deposit_id[:16]}"
        deposit_bytes = bytes.fromhex(deposit_id.removeprefix("0x"))
        tx = self._escrow.functions.refund(deposit_bytes).build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "chainId": self._settings.chain_id,
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def chain_status(self) -> dict[str, Any]:
        """Quick health report for the ``/healthz`` endpoint."""
        if not self.live:
            return {
                "mode": "dry_run",
                "service_address": self.service_address,
                "escrow": self._settings.escrow_address,
                "chain_id": self._settings.chain_id,
            }
        return {
            "mode": "live",
            "service_address": self.service_address,
            "block_number": int(self._w3.eth.block_number),
            "escrow": self._settings.escrow_address,
            "registry": self._settings.registry_address,
            "chain_id": self._settings.chain_id,
        }
