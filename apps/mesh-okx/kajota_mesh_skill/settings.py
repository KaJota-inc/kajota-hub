"""Runtime settings — all env-var driven, no defaults that would let prod boot misconfigured."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration.

    Required env vars:
      MESH_RPC_URL              — Sepolia RPC endpoint (Alchemy / Infura / Ankr)
      MESH_RELEASE_AUTH_KEY     — hex private key for the wallet authorised to call
                                  ``release`` / ``refund`` on the deployed escrow.
                                  Match against ``releaseAuth`` in the deployment manifest.
    Optional:
      MESH_REGISTRY_ADDRESS     — defaults to the Sepolia mainnet-of-testnet deploy
      MESH_ESCROW_ADDRESS       — ""
      MESH_USDC_ADDRESS         — ""
      MESH_CHAIN_ID             — 11155111
      MESH_DRY_RUN              — when true, never broadcasts; returns fake tx hashes.
                                  Used for the local smoke test + demo without a funded wallet.
    """

    model_config = SettingsConfigDict(env_prefix="MESH_", env_file=".env", extra="ignore")

    rpc_url: str = Field(default="")
    release_auth_key: str = Field(default="")
    registry_address: str = Field(default="0xfce6bd68d8d6f858d447f537d206c1e354b44315")
    escrow_address: str = Field(default="0x599869cef2e4c52e2c9074caaf8f9fb0cb191776")
    usdc_address: str = Field(default="0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    chain_id: int = 11155111
    dry_run: bool = False

    @property
    def is_live(self) -> bool:
        return bool(self.rpc_url) and bool(self.release_auth_key) and not self.dry_run
