"""Server-side x402 paywall for XLayer / OKX.AI.

EVM-native fork of ``x402_casper.py`` for the OKX.AI Genesis Hackathon. Same
protocol shape (POST ``/verify`` + ``/settle`` on any x402-compatible
facilitator), but the defaults, network id, and PaymentRequirements
``extra`` are wired for XLayer — OKX's Polygon-CDK L2 (testnet 195, mainnet
196) — settling in an ERC-20 stablecoin via EIP-3009
``transferWithAuthorization`` or Permit2.

This is the "no human sign-off" settlement rail for a Kajota Coach A2MCP
Agent Service Provider listing: the buyer's OKX.AI CLI signs an
authorisation over a fixed ERC-20 amount, ships the base64 payload in
``X-PAYMENT``, and the facilitator debits their wallet on XLayer and
returns the tx hash — all in one HTTP round-trip.

Configuration is env-driven so we can flip between Coinbase's CDP
facilitator, OKX's official facilitator (if/when published), or a
self-hosted ``coinbase/x402`` instance without a code change.

Environment (all X402_* prefix):
    X402_FACILITATOR_URL   base URL of the facilitator (no trailing /)
    X402_NETWORK           "eip155:195" (XLayer testnet) | "eip155:196"
    X402_PAY_TO            0x… recipient EOA / contract on XLayer
    X402_ASSET             0x… ERC-20 token address (USDT/USDC/KJUSD)
    X402_MAX_AMOUNT        atomic units string, e.g. "10000" (6-dec ⇒ $0.01)
    X402_ASSET_NAME        ERC-20 name for the EIP-712 domain (e.g. "USD Coin")
    X402_ASSET_VERSION     ERC-20 domain version (default "2" for EIP-3009)
    X402_ASSET_DECIMALS    "6" for USDC/USDT/KJUSD
    X402_FACILITATOR_API_KEY  bearer token, if the facilitator requires it
    X402_VERSION           "1" for Coinbase CDP, "2" for CSPR-style
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

# Coinbase's CDP x402 facilitator advertises v1 as its wire version; OKX
# may adopt v2 to match Casper. Env-override lets us follow whichever the
# selected facilitator speaks.
X402_VERSION = int(os.environ.get("X402_VERSION", "1"))

# No canonical public URL is hard-baked in — set X402_FACILITATOR_URL to
# your chosen facilitator (Coinbase CDP, OKX-hosted, or self-hosted
# `coinbase/x402`). We fail-closed at request time if unset.
DEFAULT_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "")

# CAIP-2 network ids for XLayer. Confirmed from
# `okx/onchainos-skills` `cli/src/chains.rs` — SUPPORTED_CHAIN_INDICES
# contains 195 (testnet) and 196 (mainnet).
NETWORK_MAINNET = "eip155:196"
NETWORK_TESTNET = "eip155:195"


class PaymentRequiredError(Exception):
    """Raised inside a protected handler when payment is absent or rejected.

    Carries the already-built 402 ``JSONResponse`` so the route (or an
    exception handler) can return it verbatim. Modelled as an exception
    rather than an early return so the gate composes cleanly as a FastAPI
    dependency *and* as an inline guard.
    """

    def __init__(self, response: JSONResponse) -> None:
        self.response = response
        super().__init__("x402 payment required")


@dataclass(frozen=True)
class X402Config:
    """Resolved x402 settings for one protected resource on XLayer.

    Built once from the environment (see ``from_env``) and reused per
    request. Frozen so a handler can't accidentally mutate the price
    mid-flight.
    """

    facilitator_url: str
    network: str
    pay_to: str
    asset: str
    # Atomic units of ``asset``. For a 6-decimal USDT/USDC, 10_000 = $0.01.
    max_amount_required: str
    description: str
    api_key: str = ""
    mime_type: str = "application/json"
    max_timeout_seconds: int = 60
    # EIP-712 domain hints the facilitator embeds when the buyer wallet
    # renders the price tag: token `name` / `version` (2 for USDC v2 /
    # ERC-3009), `decimals`.
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """True when enough is set to actually charge (vs. demo-stub mode)."""
        return bool(self.facilitator_url and self.pay_to and self.asset)

    @classmethod
    def from_env(cls, *, description: str) -> "X402Config":
        """Resolve config from ``X402_*`` env vars.

        Defaults to XLayer testnet (``eip155:195``) so a fresh checkout is
        safe. Facilitator URL, payTo, asset, and amount are always
        required from env — no wildcards.
        """
        extra: dict[str, Any] = {
            "name": os.environ.get("X402_ASSET_NAME", "KaJota USD"),
            "version": os.environ.get("X402_ASSET_VERSION", "2"),
            "decimals": os.environ.get("X402_ASSET_DECIMALS", "6"),
        }
        extra_raw = os.environ.get("X402_ASSET_EXTRA", "").strip()
        if extra_raw:
            try:
                extra.update(json.loads(extra_raw))
            except json.JSONDecodeError:
                pass
        return cls(
            facilitator_url=os.environ.get(
                "X402_FACILITATOR_URL", DEFAULT_FACILITATOR_URL
            ).rstrip("/"),
            network=os.environ.get("X402_NETWORK", NETWORK_TESTNET),
            pay_to=os.environ.get("X402_PAY_TO", ""),
            asset=os.environ.get("X402_ASSET", ""),
            # 10_000 base units of a 6-decimal ERC-20 = $0.01, the OKX.AI
            # A2MCP micropayment sweet spot.
            max_amount_required=os.environ.get("X402_MAX_AMOUNT", "10000"),
            description=description,
            api_key=(
                os.environ.get("X402_FACILITATOR_API_KEY")
                or os.environ.get("X402_API_KEY")
                or ""
            ),
            mime_type=os.environ.get("X402_MIME_TYPE", "application/json"),
            max_timeout_seconds=int(os.environ.get("X402_TIMEOUT_SECONDS", "60")),
            extra=extra,
        )


def build_payment_requirements(cfg: X402Config, resource: str) -> dict[str, Any]:
    """Build one x402 PaymentRequirements object (the price tag for a route).

    ``resource`` is the absolute URL of the protected endpoint; the
    facilitator binds the signature to it so a payment for
    ``/coach/premium`` can't be replayed against another route.

    Coinbase's canonical EVM shape uses ``maxAmountRequired``; the Casper
    reference facilitator reads ``amount`` instead. We emit BOTH so the
    same body works against either facilitator without a config toggle.
    """
    return {
        "scheme": "exact",
        "network": cfg.network,
        "maxAmountRequired": cfg.max_amount_required,
        "amount": cfg.max_amount_required,  # Casper-compat alias
        "resource": resource,
        "description": cfg.description,
        "mimeType": cfg.mime_type,
        "payTo": cfg.pay_to,
        "maxTimeoutSeconds": cfg.max_timeout_seconds,
        "asset": cfg.asset,
        "extra": cfg.extra,
    }


def _payment_required_response(
    cfg: X402Config, resource: str, *, error: str
) -> JSONResponse:
    """The 402 body + headers a client needs to construct its payment."""
    requirements = build_payment_requirements(cfg, resource)
    body = {
        "x402Version": X402_VERSION,
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
    """Pull the signed payment payload from the request.

    Standard header is ``X-PAYMENT``; some SDKs use ``Payment-Signature``.
    Accept either for interoperability.
    """
    return request.headers.get("X-PAYMENT") or request.headers.get("Payment-Signature")


def _decode_payment_payload(raw: str) -> dict[str, Any]:
    """Decode the ``X-PAYMENT`` header into a PaymentPayload dict.

    Clients send it base64-encoded JSON (x402 standard). Some send raw JSON;
    tolerate both so a hand-rolled ``curl`` demo doesn't fail on encoding.
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
        """base64 JSON for the ``X-PAYMENT-RESPONSE`` header (x402 standard)."""
        payload = {
            "success": self.success,
            "transaction": self.transaction,
            "network": self.network,
            "payer": self.payer,
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()


class EvmX402Facilitator:
    """Thin async client for an x402 facilitator on XLayer / EVM.

    Wraps the two endpoints required end-to-end: ``/verify`` (cheap
    signature + replay check, no chain write) and ``/settle`` (submits the
    ERC-3009 or Permit2 transfer and awaits confirmation).

    Bearer-style ``Authorization`` if ``api_key`` is set, otherwise no
    auth header (matches Coinbase CDP + most self-hosted facilitators).
    """

    def __init__(self, cfg: X402Config) -> None:
        self._cfg = cfg

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._cfg.api_key:
            headers["Authorization"] = f"Bearer {self._cfg.api_key}"
        return headers

    async def verify(
        self, payload: dict[str, Any], requirements: dict[str, Any]
    ) -> tuple[bool, str, str]:
        """POST /verify — signature + replay check, no chain write."""
        body = {
            "x402Version": X402_VERSION,
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
        """POST /settle — submit the ERC-3009/Permit2 transfer + await conf."""
        body = {
            "x402Version": X402_VERSION,
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


async def require_payment(request: Request, cfg: X402Config) -> SettlementResult:
    """Gate the current request behind a settled XLayer x402 payment.

    Call this at the top of a protected handler. Behaviour:

    * No payment header  → raise ``PaymentRequiredError`` carrying a 402
      with the price tag.
    * Header present     → verify, then settle. On any failure raise
      ``PaymentRequiredError`` (a fresh 402 so the client can retry). On
      success return the ``SettlementResult`` (the handler attaches the
      tx hash to its response).

    Fails closed on an unconfigured server: still demand payment, but the
    402 explains what's missing.
    """
    resource = str(request.url)
    raw = _read_payment_header(request)

    if not cfg.configured:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg,
                resource,
                error=(
                    "x402 paywall is not fully configured on this server "
                    "(set X402_FACILITATOR_URL, X402_PAY_TO, X402_ASSET). "
                    "See agent/README.md for OKX.AI setup."
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
    facilitator = EvmX402Facilitator(cfg)

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
