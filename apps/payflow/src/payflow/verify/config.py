import os
from typing import Optional

from pydantic import BaseModel, Field


class AnchorConfig(BaseModel):
    """On-chain anchor configuration.

    The target contract must expose a function matching `function_name` that
    takes a single `bytes32` commitment hash. The default is `anchor(bytes32)` —
    this is what the Kajota Witness contract on 0G Galileo exposes
    (`WitnessAnchor 0x2f1D3a…cEC94`), but any registry with the same signature
    will do.

    `dry_run=True` (the default) returns a computed commitment hash and the call
    data that *would* have been submitted, without touching the network. Flip to
    False only after verifying the RPC + contract are reachable.
    """
    rpc_url: str = Field(..., description="JSON-RPC endpoint for the target chain.")
    contract_address: str = Field(..., description="0x-prefixed anchor contract address.")
    chain_id: int = Field(..., description="EVM chain ID.")
    private_key: Optional[str] = Field(
        None,
        description="Hex private key for the submitter. Required when dry_run=False.",
    )
    function_name: str = Field("anchor", description="Contract function to call (takes bytes32).")
    gas_limit: int = Field(100_000, description="Static gas limit for the anchor tx.")
    dry_run: bool = Field(True, description="If True, compute call data but do not broadcast.")

    @classmethod
    def from_env(cls) -> Optional["AnchorConfig"]:
        rpc = os.environ.get("PAYFLOW_ANCHOR_RPC_URL")
        addr = os.environ.get("PAYFLOW_ANCHOR_CONTRACT")
        chain_id = os.environ.get("PAYFLOW_ANCHOR_CHAIN_ID")
        if not (rpc and addr and chain_id):
            return None
        return cls(
            rpc_url=rpc,
            contract_address=addr,
            chain_id=int(chain_id),
            private_key=os.environ.get("PAYFLOW_ANCHOR_PRIVATE_KEY"),
            function_name=os.environ.get("PAYFLOW_ANCHOR_FUNCTION", "anchor"),
            gas_limit=int(os.environ.get("PAYFLOW_ANCHOR_GAS_LIMIT", "100000")),
            dry_run=_bool_env("PAYFLOW_ANCHOR_DRY_RUN", default=True),
        )


def _bool_env(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")
