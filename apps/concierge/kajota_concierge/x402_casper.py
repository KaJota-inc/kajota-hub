"""Server-side x402 paywall for Casper Network.

This module turns any FastAPI route into a pay-per-call endpoint settled on
the Casper Network through the official CSPR.cloud x402 Facilitator. It is a
faithful, dependency-light Python port of the server half of the x402
protocol (the same envelope Coinbase standardised and the Casper reference
servers — ``make-software/casper-x402`` — implement with the ``exact`` scheme
over the ``casper:*`` CAIP-2 family).

Why we wrote our own instead of pulling a library: the only official x402
*server* SDKs are Node (``@make-software/casper-x402``) and Go. The KaJota
Coach agent is Python/FastAPI, and the facilitator itself is a plain HTTP
service — so the lean, correct move is to speak that HTTP directly rather than
stand up a Node sidecar just to proxy two POSTs.

The flow this implements (HTTP 402 "Payment Required", revived for agents):

    1. An agent (or any client) calls a protected route with no payment.
    2. We answer ``402`` with a JSON body listing ``accepts`` — the
       PaymentRequirements the caller must satisfy (asset, amount, payTo,
       network). This is the price tag.
    3. The agent signs an EIP-712 ``transfer_with_authorization`` over a
       CEP-18 token and retries with the signed payload in the ``X-PAYMENT``
       header.
    4. We forward {payload, requirements} to the facilitator's ``/verify``
       (cheap signature/replay check) and then ``/settle`` (submits the
       on-chain CEP-18 transfer and waits for confirmation).
    5. On success we run the protected handler and return the settlement
       receipt (the Casper deploy hash) in the ``X-PAYMENT-RESPONSE`` header
       so the caller — and our demo — has on-chain proof.

Everything is configured from the environment so the same code runs against
testnet (``casper:casper-test``) in the demo and mainnet in production.
Nothing here imports the ADK agent, so it can be unit-tested in isolation.
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

# The x402 envelope version we speak. The live CSPR.cloud facilitator
# advertises v2 on GET /supported (verified Jun 27, 2026) and reads the price
# field as `amount` (NOT the x402-standard `maxAmountRequired`) — confirmed by
# probing /verify. Override via X402_VERSION if the facilitator moves again.
X402_VERSION = int(os.environ.get("X402_VERSION", "2"))

# Default CSPR.cloud facilitator. Same host serves mainnet and testnet; the
# network is selected per-request via the PaymentRequirements ``network``.
DEFAULT_FACILITATOR_URL = "https://x402-facilitator.cspr.cloud"

# CAIP-2 network ids the facilitator understands.
NETWORK_MAINNET = "casper:casper"
NETWORK_TESTNET = "casper:casper-test"


class PaymentRequiredError(Exception):
    """Raised inside a protected handler when payment is absent or rejected.

    Carries the already-built 402 ``JSONResponse`` so the route (or an
    exception handler) can return it verbatim. We model this as an exception
    rather than returning early so the gate composes cleanly as a FastAPI
    dependency *and* as an inline guard.
    """

    def __init__(self, response: JSONResponse) -> None:
        self.response = response
        super().__init__("x402 payment required")


@dataclass(frozen=True)
class X402Config:
    """Resolved x402 settings for one protected resource.

    Built once from the environment (see ``from_env``) and reused per request.
    Frozen so a handler can't accidentally mutate the price mid-flight.
    """

    facilitator_url: str
    network: str
    pay_to: str
    asset: str
    # Atomic units of ``asset``. The Casper reference servers settle in WCSPR
    # (9 decimals), so 1_000_000 == 0.001 WCSPR — the canonical "$0.001"
    # micropayment. Scale to your token's decimals if you use a different one.
    max_amount_required: str
    description: str
    # Bearer/opaque token for the facilitator. The buildathon hands teams a
    # sponsored CSPR.cloud key; without it every facilitator call is 401.
    api_key: str = ""
    mime_type: str = "application/json"
    max_timeout_seconds: int = 60
    # CEP-18 EIP-712 domain hints (name/version/decimals). The facilitator can
    # infer these, but passing them through ``extra`` makes the price tag
    # self-describing for wallets that render it.
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """True when enough is set to actually charge (vs. demo-stub mode)."""
        return bool(self.pay_to and self.asset and self.api_key)

    @classmethod
    def from_env(cls, *, description: str) -> "X402Config":
        """Resolve config from ``X402_*`` env vars.

        Falls back to the CSPR.cloud facilitator and testnet so a fresh
        checkout points at the safe network by default. ``X402_API_KEY``
        falls back to ``CSPR_CLOUD_API_KEY`` since the buildathon issues one
        sponsored key that unlocks both the facilitator and CSPR.cloud.
        """
        # Build the CEP-18 `extra` the facilitator needs: a non-empty
        # `version` is mandatory (it seeds the EIP-712 domain), plus token
        # `name`/`decimals`. Defaults describe WCSPR (what Casper's reference
        # servers settle in). `feePayer` is the facilitator's sponsored gas
        # account — fetch it from GET /supported and set X402_FEE_PAYER.
        # A raw X402_ASSET_EXTRA JSON blob, if given, overrides these.
        extra: dict[str, Any] = {
            "name": os.environ.get("X402_ASSET_NAME", "WCSPR"),
            "version": os.environ.get("X402_ASSET_VERSION", "1"),
            "decimals": os.environ.get("X402_ASSET_DECIMALS", "9"),
        }
        fee_payer = os.environ.get("X402_FEE_PAYER", "").strip()
        if fee_payer:
            extra["feePayer"] = fee_payer
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
            max_amount_required=os.environ.get("X402_MAX_AMOUNT", "1000000"),
            description=description,
            api_key=(
                os.environ.get("X402_FACILITATOR_API_KEY")
                or os.environ.get("X402_API_KEY")
                or os.environ.get("CSPR_CLOUD_API_KEY")
                or ""
            ),
            mime_type=os.environ.get("X402_MIME_TYPE", "application/json"),
            max_timeout_seconds=int(os.environ.get("X402_TIMEOUT_SECONDS", "60")),
            extra=extra,
        )


def build_payment_requirements(cfg: X402Config, resource: str) -> dict[str, Any]:
    """Build one x402 PaymentRequirements object (the price tag for a route).

    ``resource`` is the absolute URL of the protected endpoint; the facilitator
    binds the signature to it so a payment for ``/coach/premium`` can't be
    replayed against another route.
    """
    return {
        "scheme": "exact",
        "network": cfg.network,
        # Casper's facilitator reads `amount` (not the x402-standard
        # `maxAmountRequired`). Atomic units of the CEP-18 asset.
        "amount": cfg.max_amount_required,
        "resource": resource,
        "description": cfg.description,
        "mimeType": cfg.mime_type,
        # Recipient account-hash, "00"-prefixed (NOT a public key).
        "payTo": cfg.pay_to,
        "maxTimeoutSeconds": cfg.max_timeout_seconds,
        # CEP-18 contract package hash (must implement transfer_with_authorization).
        "asset": cfg.asset,
        # extra MUST carry a non-empty `version` (EIP-712 domain) and the
        # token `name`/`decimals`; `feePayer` (the facilitator's sponsored gas
        # account) is echoed from GET /supported when known.
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
    # Mirror the requirements into a header too — the Casper reference servers
    # expose ``PAYMENT-REQUIRED``; some clients read the header, others the
    # body. Provide both.
    header_blob = base64.b64encode(json.dumps(requirements).encode()).decode()
    return JSONResponse(
        status_code=402,
        content=body,
        headers={
            "PAYMENT-REQUIRED": header_blob,
            # Let browser-based agents read the settlement header on success.
            "Access-Control-Expose-Headers": "PAYMENT-REQUIRED, X-PAYMENT-RESPONSE",
        },
    )


def _read_payment_header(request: Request) -> str | None:
    """Pull the signed payment payload from the request.

    The x402 standard header is ``X-PAYMENT``; the Casper examples also use
    ``Payment-Signature``. Accept either so we interoperate with both client
    SDKs. Header lookup is case-insensitive via Starlette's ``Headers``.
    """
    return request.headers.get("X-PAYMENT") or request.headers.get("Payment-Signature")


def _decode_payment_payload(raw: str) -> dict[str, Any]:
    """Decode the ``X-PAYMENT`` header into a PaymentPayload dict.

    Clients send it base64-encoded JSON (x402 standard). Some send raw JSON;
    tolerate both so a hand-rolled ``curl`` demo doesn't fail on encoding.
    """
    raw = raw.strip()
    # Try base64 first (the standard), then fall back to raw JSON.
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


class CasperX402Facilitator:
    """Thin async client for the CSPR.cloud x402 Facilitator.

    Wraps the three endpoints we need — ``/supported``, ``/verify``,
    ``/settle`` — each a POST (``/supported`` a GET) of
    ``{x402Version, paymentPayload, paymentRequirements}`` authorised by the
    sponsored CSPR.cloud key.
    """

    def __init__(self, cfg: X402Config) -> None:
        self._cfg = cfg

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._cfg.api_key:
            # The Casper reference server sends the key as the raw
            # Authorization value (no "Bearer " prefix).
            headers["Authorization"] = self._cfg.api_key
        return headers

    async def verify(
        self, payload: dict[str, Any], requirements: dict[str, Any]
    ) -> tuple[bool, str, str]:
        """POST /verify — signature + replay check, no chain write.

        Returns ``(is_valid, payer, invalid_reason)``.
        """
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
        """POST /settle — submit the CEP-18 transfer and await confirmation."""
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
    """Gate the current request behind a settled Casper x402 payment.

    Call this at the top of a protected handler. Behaviour:

    * No payment header  → raise ``PaymentRequiredError`` carrying a 402 with
      the price tag.
    * Header present     → verify, then settle on Casper. On any failure raise
      ``PaymentRequiredError`` (a fresh 402, so the client can retry). On
      success return the ``SettlementResult`` (the handler attaches the deploy
      hash to its response).

    If the resource isn't fully configured (no payTo/asset/key — e.g. a clean
    checkout with no sponsored key yet), we *fail closed*: still demand
    payment, but the 402 explains the server is unconfigured. This keeps the
    paywall honest in the demo rather than silently letting calls through.
    """
    resource = f"{request.headers.get('x-forwarded-proto') or request.url.scheme}://{request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc}{request.headers.get('x-forwarded-prefix', '')}{request.url.path}"
    raw = _read_payment_header(request)

    if not cfg.configured:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg,
                resource,
                error=(
                    "x402 paywall is not fully configured on this server "
                    "(set X402_PAY_TO, X402_ASSET, and a sponsored "
                    "X402_FACILITATOR_API_KEY). See agent/README.md."
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
    facilitator = CasperX402Facilitator(cfg)

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
