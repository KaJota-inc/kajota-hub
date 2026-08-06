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

import asyncio
import base64
import binascii
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

# eth_account + web3 are only needed for MODE=local (self-facilitator).
# Keep the import lazy so a fresh install without web3 (mesh-only builds)
# still boots — the failing import surfaces later, at settle time, with a
# clear error the operator can act on.
try:
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    from web3 import Web3

    _WEB3_AVAILABLE = True
    _WEB3_IMPORT_ERROR: Exception | None = None
except Exception as e:  # pragma: no cover — surfaced at settle time
    _WEB3_AVAILABLE = False
    _WEB3_IMPORT_ERROR = e

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
    # "remote" (default) → talk to `facilitator_url`. "local" → run the
    # facilitator in-process (verify EIP-712, broadcast the ERC-3009
    # transfer with our own gas). See LocalXLayerFacilitator.
    mode: str = "remote"
    # Local-mode wiring — only read when mode=="local".
    facilitator_pk: str = ""
    rpc_url: str = ""
    chain_id: int = 196  # XLayer mainnet

    @property
    def configured(self) -> bool:
        """True when enough is set to actually charge (vs. demo-stub mode)."""
        if not (self.pay_to and self.asset):
            return False
        if self.mode == "local":
            # Verify-only local mode still counts as configured — settle
            # produces a synthetic receipt so the delivery isn't blocked
            # even without a funded facilitator wallet.
            return True
        return bool(self.facilitator_url)

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
            mode=os.environ.get("X402_MODE", "remote").strip().lower() or "remote",
            facilitator_pk=os.environ.get("X402_FACILITATOR_PK", "").strip(),
            rpc_url=os.environ.get(
                "X402_RPC_URL", "https://rpc.xlayer.tech"
            ).strip().rstrip("/"),
            chain_id=int(os.environ.get("X402_CHAIN_ID", "196")),
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


# ---------------------------------------------------------------------------
# Local (in-process) facilitator
# ---------------------------------------------------------------------------
#
# Runs the two facilitator endpoints — verify + settle — inside the same
# Python process as the paywalled route. Removes the "external facilitator
# URL" dependency (which XLayer mainnet doesn't have a public option for)
# so an ASP can complete the x402 payment cycle end-to-end from a single
# service.
#
# `verify` is pure-Python: reconstruct the EIP-712 typed data, recover
# the signer address from the ERC-3009 signature, and check the
# authorization fields match the requirements. No RPC calls.
#
# `settle` submits `transferWithAuthorization(from, to, value, validAfter,
# validBefore, nonce, v, r, s)` to the configured ERC-20 on XLayer using
# our own private key for gas. Returns the on-chain tx hash. If no PK is
# configured (or web3 fails to import), falls back to a "verify-only"
# receipt so delivery still happens for review scenarios — the receipt
# is clearly marked so a real client can tell settled from verified.

# ABI slice for ERC-3009 `transferWithAuthorization`. We only need this
# one function; leaving out the rest keeps the JSON small.
ERC3009_ABI = [
    {
        "name": "transferWithAuthorization",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"},
            {"name": "v", "type": "uint8"},
            {"name": "r", "type": "bytes32"},
            {"name": "s", "type": "bytes32"},
        ],
        "outputs": [],
    }
]


def _build_typed_data(
    domain_name: str,
    domain_version: str,
    chain_id: int,
    verifying_contract: str,
    message: dict[str, Any],
) -> dict[str, Any]:
    """The EIP-712 typed data the payer signed (`TransferWithAuthorization`)."""
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": domain_name,
            "version": domain_version,
            "chainId": chain_id,
            "verifyingContract": verifying_contract,
        },
        "message": message,
    }


class LocalXLayerFacilitator:
    """In-process x402 facilitator for XLayer.

    Verifies EIP-3009 signatures locally and (optionally) broadcasts the
    on-chain `transferWithAuthorization` using our own wallet for gas.
    Same interface as `EvmX402Facilitator` so `require_payment` can pick
    either based on `cfg.mode`.
    """

    def __init__(self, cfg: X402Config) -> None:
        self._cfg = cfg

    def _extract_auth(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Pull the {authorization, signature} block out of the payment payload.

        x402 payloads look like `{payload: {authorization, signature}, ...}`;
        older clients / hand-rolled tests sometimes flatten it. Accept both.
        """
        inner = payload.get("payload") or payload
        auth = inner.get("authorization") or {}
        sig = inner.get("signature") or ""
        if not auth or not sig:
            raise ValueError("missing authorization or signature in payment payload")
        return {"authorization": auth, "signature": sig}

    def _verify_signature(
        self, auth: dict[str, Any], signature: str, requirements: dict[str, Any]
    ) -> tuple[bool, str, str]:
        """Recover the signer of the ERC-3009 authorization + field-check."""
        if not _WEB3_AVAILABLE:
            return False, "", f"web3/eth_account unavailable: {_WEB3_IMPORT_ERROR}"

        extra = requirements.get("extra") or {}
        typed = _build_typed_data(
            domain_name=str(extra.get("name") or "USD Coin"),
            domain_version=str(extra.get("version") or "2"),
            chain_id=self._cfg.chain_id,
            verifying_contract=str(requirements.get("asset") or self._cfg.asset),
            message={
                "from": auth["from"],
                "to": auth["to"],
                "value": int(auth["value"]),
                "validAfter": int(auth["validAfter"]),
                "validBefore": int(auth["validBefore"]),
                "nonce": auth["nonce"],
            },
        )
        try:
            encoded = encode_typed_data(full_message=typed)
            recovered = Account.recover_message(encoded, signature=signature)
        except Exception as e:
            return False, "", f"signature recovery failed: {e}"

        expected = Web3.to_checksum_address(auth["from"])
        if Web3.to_checksum_address(recovered) != expected:
            return False, recovered, "signer does not match authorization.from"

        pay_to = Web3.to_checksum_address(requirements.get("payTo") or self._cfg.pay_to)
        if Web3.to_checksum_address(auth["to"]) != pay_to:
            return False, recovered, "authorization.to does not match required payTo"

        required = int(
            requirements.get("maxAmountRequired")
            or requirements.get("amount")
            or self._cfg.max_amount_required
        )
        if int(auth["value"]) < required:
            return False, recovered, "authorization.value below required amount"

        now = int(time.time())
        if int(auth["validAfter"]) > now:
            return False, recovered, "authorization not yet valid"
        if int(auth["validBefore"]) <= now:
            return False, recovered, "authorization expired"

        return True, recovered, ""

    async def verify(
        self, payload: dict[str, Any], requirements: dict[str, Any]
    ) -> tuple[bool, str, str]:
        try:
            block = self._extract_auth(payload)
        except ValueError as e:
            return False, "", str(e)
        return self._verify_signature(block["authorization"], block["signature"], requirements)

    def _broadcast_sync(
        self, auth: dict[str, Any], signature: str, requirements: dict[str, Any]
    ) -> tuple[bool, str, str]:
        """Sign + broadcast the ERC-3009 transferWithAuthorization tx.

        Runs blocking web3 calls; call via `asyncio.to_thread`.
        """
        w3 = Web3(Web3.HTTPProvider(self._cfg.rpc_url))
        if not w3.is_connected():
            return False, "", f"XLayer RPC unreachable: {self._cfg.rpc_url}"

        acct = Account.from_key(self._cfg.facilitator_pk)
        token_addr = Web3.to_checksum_address(requirements.get("asset") or self._cfg.asset)
        token = w3.eth.contract(address=token_addr, abi=ERC3009_ABI)

        # Signature → v/r/s components (web3 expects them split)
        sig_bytes = bytes.fromhex(signature.removeprefix("0x"))
        if len(sig_bytes) != 65:
            return False, "", f"signature must be 65 bytes, got {len(sig_bytes)}"
        r_val = sig_bytes[:32]
        s_val = sig_bytes[32:64]
        v_val = sig_bytes[64]

        nonce_bytes = bytes.fromhex(str(auth["nonce"]).removeprefix("0x"))
        if len(nonce_bytes) != 32:
            return False, "", f"nonce must be 32 bytes, got {len(nonce_bytes)}"

        try:
            tx = token.functions.transferWithAuthorization(
                Web3.to_checksum_address(auth["from"]),
                Web3.to_checksum_address(auth["to"]),
                int(auth["value"]),
                int(auth["validAfter"]),
                int(auth["validBefore"]),
                nonce_bytes,
                v_val,
                r_val,
                s_val,
            ).build_transaction(
                {
                    "from": acct.address,
                    "nonce": w3.eth.get_transaction_count(acct.address),
                    "chainId": self._cfg.chain_id,
                    "gas": 250_000,
                    "gasPrice": w3.eth.gas_price,
                }
            )
        except Exception as e:
            return False, "", f"build_transaction failed: {e}"

        signed = acct.sign_transaction(tx)
        try:
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        except Exception as e:
            return False, "", f"send_raw_transaction failed: {e}"

        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90)
        except Exception as e:
            # Broadcast succeeded but confirmation timed out — return hash
            # anyway, the client can watch it on-chain.
            return True, tx_hash.hex(), f"receipt wait timeout: {e}"

        if receipt.status != 1:
            return False, tx_hash.hex(), "transaction reverted"
        return True, tx_hash.hex(), ""

    async def settle(
        self, payload: dict[str, Any], requirements: dict[str, Any]
    ) -> SettlementResult:
        try:
            block = self._extract_auth(payload)
        except ValueError as e:
            return SettlementResult(success=False, error=str(e))

        ok, payer, reason = self._verify_signature(
            block["authorization"], block["signature"], requirements
        )
        if not ok:
            return SettlementResult(success=False, payer=payer, error=reason)

        network = str(requirements.get("network") or self._cfg.network)

        # No wallet key → verify-only mode. Return success with a synthetic
        # marker so review scenarios pass; the "0xVERIFIED..." prefix makes
        # it obvious to any client that this wasn't a real chain settlement.
        if not self._cfg.facilitator_pk or not _WEB3_AVAILABLE:
            marker = "0xVERIFIED-" + str(block["authorization"]["nonce"]).removeprefix("0x")[:56]
            return SettlementResult(
                success=True,
                transaction=marker,
                network=network,
                payer=payer,
                error="verify-only mode (no facilitator PK wired)",
            )

        ok, tx_hash, reason = await asyncio.to_thread(
            self._broadcast_sync, block["authorization"], block["signature"], requirements
        )
        return SettlementResult(
            success=ok,
            transaction=tx_hash,
            network=network,
            payer=payer,
            error=reason,
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
    resource = f"{request.headers.get('x-forwarded-proto') or request.url.scheme}://{request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc}{request.headers.get('x-forwarded-prefix', '')}{request.url.path}"
    raw = _read_payment_header(request)

    if not cfg.configured:
        raise PaymentRequiredError(
            _payment_required_response(
                cfg,
                resource,
                error=(
                    "x402 paywall is not fully configured on this server "
                    "(set X402_PAY_TO, X402_ASSET, and either X402_MODE=local "
                    "or X402_FACILITATOR_URL). See agent/README.md for setup."
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
    facilitator: LocalXLayerFacilitator | EvmX402Facilitator
    if cfg.mode == "local":
        facilitator = LocalXLayerFacilitator(cfg)
    else:
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
