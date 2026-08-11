"""Server-side x402 paywall for Ethereum-family chains (USDC settled).

Parallel to :mod:`x402_casper` — that module handles the Casper `exact`
scheme with CEP-18 via the CSPR.cloud facilitator; this one handles the
canonical Coinbase `exact` scheme with an ERC-20 (USDC by default) via
the reference x402 facilitator (`x402.org/facilitator`), and is what
gates the KeeperHub-triggered escrow-release endpoint.

The wire format differs from Casper on three points, all set here:

* The x402 standard field is ``maxAmountRequired`` — Casper's facilitator
  quirks-reads ``amount`` (see the note in `x402_casper.py`).
* The facilitator ``Authorization`` header is a ``Bearer`` token; the
  Casper reference sends the key raw.
* Coinbase's facilitator advertises ``x402Version = 1``. Override via
  ``ETH_X402_VERSION`` if a downstream facilitator moves to v2.

Configured from the environment, so the same code runs against Base
Sepolia in the demo and Base mainnet (or Ethereum Sepolia) in production.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

# Coinbase's live facilitator was verified to advertise v1 as of the
# hackathon build window; set ETH_X402_VERSION if that changes.
ETH_X402_VERSION = int(os.environ.get("ETH_X402_VERSION", "1"))

# Coinbase-operated reference facilitator. Same host serves multiple
# EVM chains; per-request routing is via PaymentRequirements.network.
DEFAULT_FACILITATOR_URL = "https://x402.org/facilitator"

# CAIP-2 network ids common to this project.
NETWORK_BASE_MAINNET = "base"           # Coinbase facilitator dialect
NETWORK_BASE_SEPOLIA = "base-sepolia"
NETWORK_ETHEREUM_MAINNET = "ethereum"
NETWORK_ETHEREUM_SEPOLIA = "ethereum-sepolia"

# USDC on Base Sepolia — Circle testnet USDC, the cheap demo target.
USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"


class PaymentRequiredError(Exception):
    """Raised inside a protected handler when payment is absent or rejected."""

    def __init__(self, response: JSONResponse) -> None:
        self.response = response
        super().__init__("x402 payment required")


@dataclass(frozen=True)
class EthereumX402Config:
    """Resolved x402 settings for one protected resource on Ethereum.

    Built once from the environment (see ``from_env``) and reused per
    request. Frozen so a handler can't accidentally mutate the price.
    """

    facilitator_url: str
    network: str
    pay_to: str
    asset: str
    # Atomic units of ``asset``. USDC has 6 decimals, so 10_000 == $0.01.
    max_amount_required: str
    description: str
    api_key: str = ""
    mime_type: str = "application/json"
    max_timeout_seconds: int = 60
    # EIP-712 domain hints (name/version/decimals). For USDC:
    # name="USD Coin", version="2", decimals="6".
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """True when enough is set to actually charge (vs. demo-stub mode)."""
        return bool(self.pay_to and self.asset)

    @classmethod
    def from_env(cls, *, description: str) -> "EthereumX402Config":
        """Resolve config from ``ETH_X402_*`` env vars.

        Defaults point at the Coinbase facilitator + Base Sepolia + Circle
        testnet USDC so a fresh checkout is demo-runnable with just a
        ``ETH_X402_PAY_TO`` (the merchant address).
        """
        extra: dict[str, Any] = {
            "name": os.environ.get("ETH_X402_ASSET_NAME", "USD Coin"),
            "version": os.environ.get("ETH_X402_ASSET_VERSION", "2"),
            "decimals": os.environ.get("ETH_X402_ASSET_DECIMALS", "6"),
        }
        extra_raw = os.environ.get("ETH_X402_ASSET_EXTRA", "").strip()
        if extra_raw:
            try:
                extra.update(json.loads(extra_raw))
            except json.JSONDecodeError:
                pass
        return cls(
            facilitator_url=os.environ.get(
                "ETH_X402_FACILITATOR_URL", DEFAULT_FACILITATOR_URL
            ).rstrip("/"),
            network=os.environ.get("ETH_X402_NETWORK", NETWORK_BASE_SEPOLIA),
            pay_to=os.environ.get("ETH_X402_PAY_TO", ""),
            asset=os.environ.get("ETH_X402_ASSET", USDC_BASE_SEPOLIA),
            # 0.01 USDC ($0.01) by default — the smallest amount that stays
            # visible on-chain without dust concerns.
            max_amount_required=os.environ.get("ETH_X402_MAX_AMOUNT", "10000"),
            description=description,
            api_key=os.environ.get("ETH_X402_FACILITATOR_API_KEY", ""),
            mime_type=os.environ.get("ETH_X402_MIME_TYPE", "application/json"),
            max_timeout_seconds=int(os.environ.get("ETH_X402_TIMEOUT_SECONDS", "60")),
            extra=extra,
        )


def build_payment_requirements(
    cfg: EthereumX402Config, resource: str
) -> dict[str, Any]:
    """Build one x402 PaymentRequirements object.

    Uses the canonical ``maxAmountRequired`` field (not Casper's
    ``amount``) and the standard Coinbase-facilitator shape.
    """
    return {
        "scheme": "exact",
        "network": cfg.network,
        "maxAmountRequired": cfg.max_amount_required,
        "resource": resource,
        "description": cfg.description,
        "mimeType": cfg.mime_type,
        # Merchant EOA (or receiving contract) address.
        "payTo": cfg.pay_to,
        "maxTimeoutSeconds": cfg.max_timeout_seconds,
        # ERC-20 contract address (USDC on the chosen network).
        "asset": cfg.asset,
        # EIP-712 domain hints so client wallets can render a friendly
        # signing prompt without probing the token themselves.
        "extra": cfg.extra,
    }


def _payment_required_response(
    cfg: EthereumX402Config, resource: str, *, error: str
) -> JSONResponse:
    requirements = build_payment_requirements(cfg, resource)
    body = {
        "x402Version": ETH_X402_VERSION,
        "accepts": [requirements],
        "error": error,
    }
    header_blob = base64.b64encode(json.dumps(requirements).encode()).decode()
    return JSONResponse(
        status_code=402,
        content=body,
        headers={
            "PAYMENT-REQUIRED": header_blob,
            "Access-Control-Expose-Headers": "PAYMENT-REQUIRED, X-PAYMENT-RESPONSE",
        },
    )


def _read_payment_header(request: Request) -> str | None:
    """Pull the signed payment payload — accept both x402 header aliases."""
    return request.headers.get("X-PAYMENT") or request.headers.get("Payment-Signature")


def _decode_payment_payload(raw: str) -> dict[str, Any]:
    """Decode the ``X-PAYMENT`` header into a PaymentPayload dict.

    Standard is base64(JSON); tolerate raw JSON so a hand-rolled curl
    demo doesn't fail on encoding.
    """
    raw = raw.strip()
    try:
        decoded = base64.b64decode(raw, validate=True).decode()
        return json.loads(decoded)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        pass
    return json.loads(raw)


@dataclass(frozen=True)
class SettlementResult:
    """Outcome of a facilitator ``/settle`` — the on-chain receipt."""

    success: bool
    transaction: str = ""
    network: str = ""
    payer: str = ""
    error: str = ""

    def response_header(self) -> str:
        payload = {
            "success": self.success,
            "transaction": self.transaction,
            "network": self.network,
            "payer": self.payer,
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()


class EthereumX402Facilitator:
    """Thin async client for the Coinbase reference x402 facilitator."""

    def __init__(self, cfg: EthereumX402Config) -> None:
        self._cfg = cfg

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._cfg.api_key:
            # Coinbase's facilitator expects a Bearer token.
            headers["Authorization"] = f"Bearer {self._cfg.api_key}"
        return headers

    async def verify(
        self, payload: dict[str, Any], requirements: dict[str, Any]
    ) -> tuple[bool, str, str]:
        body = {
            "x402Version": ETH_X402_VERSION,
            "paymentPayload": payload,
            "paymentRequirements": requirements,
        }
        async with httpx.AsyncClient(timeout=self._cfg.max_timeout_seconds) as client:
            resp = await client.post(
                f"{self._cfg.facilitator_url}/verify",
                headers=self._headers(),
                json=body,
            )
        if resp.status_code != 200:
            return False, "", f"facilitator /verify HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        return (
            bool(data.get("isValid")),
            str(data.get("payer", "")),
            str(data.get("invalidReason") or ""),
        )

    async def settle(
        self, payload: dict[str, Any], requirements: dict[str, Any]
    ) -> SettlementResult:
        body = {
            "x402Version": ETH_X402_VERSION,
            "paymentPayload": payload,
            "paymentRequirements": requirements,
        }
        async with httpx.AsyncClient(timeout=self._cfg.max_timeout_seconds) as client:
            resp = await client.post(
                f"{self._cfg.facilitator_url}/settle",
                headers=self._headers(),
                json=body,
            )
        if resp.status_code != 200:
            return SettlementResult(
                success=False,
                error=f"facilitator /settle HTTP {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
        return SettlementResult(
            success=bool(data.get("success")),
            transaction=str(data.get("transaction", "")),
            network=str(data.get("network", requirements.get("network", ""))),
            payer=str(data.get("payer", "")),
            error=str(data.get("errorReason") or ""),
        )


async def require_payment(
    request: Request, cfg: EthereumX402Config
) -> SettlementResult:
    """Gate the current request behind a settled Ethereum x402 payment.

    Same contract as :func:`x402_casper.require_payment`:

    * No payment header  → raise ``PaymentRequiredError`` with a 402
      response carrying the price tag.
    * Header present     → verify, then settle on the configured network.
      Any failure raises a fresh ``PaymentRequiredError`` (so the client
      can retry). Success returns a ``SettlementResult`` — the handler
      attaches the settlement tx hash to its response.

    If the resource isn't fully configured (no payTo/asset — e.g. a
    fresh checkout), we *fail closed*: still demand payment, but the
    402 explains what's missing.
    """
    resource = (
        f"{request.headers.get('x-forwarded-proto') or request.url.scheme}"
        f"://{request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc}"
        f"{request.headers.get('x-forwarded-prefix', '')}"
        f"{request.url.path}"
    )
    raw = _read_payment_header(request)

    if not cfg.configured:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg,
                resource,
                error=(
                    "x402 paywall is not fully configured on this server "
                    "(set ETH_X402_PAY_TO and ETH_X402_ASSET). See "
                    "agent/KEEPERHUB.md."
                ),
            )
        )

    if not raw:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg, resource, error="X-PAYMENT header is required"
            )
        )

    try:
        payload = _decode_payment_payload(raw)
    except (ValueError, json.JSONDecodeError):
        raise PaymentRequiredError(
            _payment_required_response(
                cfg, resource, error="malformed X-PAYMENT header (expected base64 JSON)"
            )
        )

    requirements = build_payment_requirements(cfg, resource)
    facilitator = EthereumX402Facilitator(cfg)

    is_valid, _payer, reason = await facilitator.verify(payload, requirements)
    if not is_valid:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg, resource, error=f"payment verification failed: {reason}"
            )
        )

    result = await facilitator.settle(payload, requirements)
    if not result.success:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg, resource, error=f"settlement failed: {result.error}"
            )
        )
    return result
