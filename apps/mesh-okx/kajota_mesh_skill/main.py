"""FastAPI app — agent-callable escrow surface."""

from __future__ import annotations

from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from kajota_mesh_skill.mesh import MeshClient
from kajota_mesh_skill.settings import Settings

app = FastAPI(
    title="KaJota Mesh Skill",
    description="On-chain escrow as a NANDA-discoverable skill. Agents lock, release, "
    "and dispute USDC on Ethereum Sepolia via a single service wallet — no key "
    "management required on the agent side.",
    version="0.1.0",
)

_settings = Settings()
_client = MeshClient(_settings)


def get_client() -> MeshClient:
    return _client


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    ok: bool
    mode: str
    service_address: str
    chain_id: int
    extra: dict[str, object] = Field(default_factory=dict)


class QuoteRequest(BaseModel):
    amount_usd: float = Field(gt=0, description="Gross amount in human-readable USD.")


class QuoteResponse(BaseModel):
    gross_amount_units: int = Field(description="USDC base units (6 decimals).")
    fee_amount_units: int = Field(description="Service fee in USDC base units (currently 0).")
    net_amount_units: int = Field(description="Net to seller in USDC base units.")
    currency: str = "USDC"


class DepositResponse(BaseModel):
    deposit_id: str
    listing_id: str
    buyer: str
    seller: str
    gross_amount_units: int
    fee_amount_units: int
    net_amount_units: int
    status: str


class ActionRequest(BaseModel):
    deposit_id: str = Field(
        description="The on-chain deposit id (0x-prefixed 32-byte hex) returned at "
        "lock time by the CosellEscrow.Deposited event."
    )


class ActionResponse(BaseModel):
    deposit_id: str
    action: str  # "release" | "refund"
    tx_hash: str
    explorer_url: str


def _explorer_url_for_tx(tx_hash: str, chain_id: int) -> str:
    if chain_id == 11155111:
        return f"https://sepolia.etherscan.io/tx/{tx_hash}"
    return f"https://etherscan.io/tx/{tx_hash}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/healthz", response_model=HealthResponse, tags=["meta"])
def healthz(client: Annotated[MeshClient, Depends(get_client)]) -> HealthResponse:
    status = client.chain_status()
    return HealthResponse(
        ok=True,
        mode=str(status["mode"]),
        service_address=str(status["service_address"]),
        chain_id=int(status["chain_id"]),
        extra={k: v for k, v in status.items() if k not in {"mode", "service_address", "chain_id"}},
    )


@app.post("/escrow/quote", response_model=QuoteResponse, tags=["escrow"])
def quote(body: QuoteRequest) -> QuoteResponse:
    """Convert a human-readable USD amount into USDC base units.

    USDC has 6 decimal places; this endpoint is purely informational and does
    not touch chain state.  Agents should call it before ``/escrow/lock`` so
    they understand the on-chain unit they'll be charged.
    """
    units = int(round(body.amount_usd * 1_000_000))
    return QuoteResponse(
        gross_amount_units=units,
        fee_amount_units=0,
        net_amount_units=units,
    )


@app.get("/escrow/deposit/{deposit_id}", response_model=DepositResponse, tags=["escrow"])
def get_deposit(
    deposit_id: str,
    client: Annotated[MeshClient, Depends(get_client)],
) -> DepositResponse:
    """Read on-chain state for a deposit by id."""
    view = client.get_deposit(deposit_id)
    if view is None:
        raise HTTPException(404, f"deposit {deposit_id} not found (or dry-run mode)")
    return DepositResponse(
        deposit_id=view.deposit_id,
        listing_id=view.listing_id,
        buyer=view.buyer,
        seller=view.seller,
        gross_amount_units=view.gross_amount,
        fee_amount_units=view.fee_amount,
        net_amount_units=view.net_amount,
        status=view.status,
    )


@app.post("/escrow/release", response_model=ActionResponse, tags=["escrow"])
def release(
    body: ActionRequest,
    client: Annotated[MeshClient, Depends(get_client)],
) -> ActionResponse:
    """Release the escrowed USDC to the seller.

    Authorised by the service wallet (matches ``releaseAuth`` on the
    deployed escrow).  Agents should call this once they have verified
    delivery off-chain.
    """
    tx_hash = client.release(body.deposit_id)
    return ActionResponse(
        deposit_id=body.deposit_id,
        action="release",
        tx_hash=tx_hash,
        explorer_url=_explorer_url_for_tx(tx_hash, _settings.chain_id),
    )


@app.post("/escrow/refund", response_model=ActionResponse, tags=["escrow"])
def refund(
    body: ActionRequest,
    client: Annotated[MeshClient, Depends(get_client)],
) -> ActionResponse:
    """Refund the escrowed USDC to the buyer.

    Authorised by the service wallet.  Use when delivery did not occur
    or both parties agree to cancel.
    """
    tx_hash = client.refund(body.deposit_id)
    return ActionResponse(
        deposit_id=body.deposit_id,
        action="refund",
        tx_hash=tx_hash,
        explorer_url=_explorer_url_for_tx(tx_hash, _settings.chain_id),
    )


def run() -> None:
    """Entry-point for ``kajota-mesh-skill`` script + Render PORT env var."""
    import os

    uvicorn.run("kajota_mesh_skill.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8081")))


if __name__ == "__main__":
    run()
