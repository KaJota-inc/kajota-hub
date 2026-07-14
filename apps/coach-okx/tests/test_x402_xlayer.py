"""Unit tests for the XLayer / EVM x402 paywall (``x402_xlayer``).

Mirrors the Casper test suite (12 tests, hermetic, no network) but with EVM
semantics for the OKX.AI Genesis Hackathon: eip155 CAIP-2 network id, ERC-20
`asset` addresses, `maxAmountRequired` + `amount` dual-emit for facilitator
compat, and Coinbase-style Bearer auth on the facilitator API key.

Runs with just fastapi + httpx + pytest (no ADK, no live facilitator).
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from starlette.requests import Request

from kajota_concierge import x402_xlayer as x


# ---- helpers ------------------------------------------------------


def _make_request(headers: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request for ``require_payment``."""
    raw_headers = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "server": ("api.kajota.test", 443),
        "path": "/coach/premium",
        "query_string": b"",
        "headers": raw_headers,
    }
    return Request(scope)


def _configured_cfg(**overrides) -> x.X402Config:
    base = dict(
        facilitator_url="https://x402.example.com",
        network=x.NETWORK_TESTNET,
        pay_to="0x0000000000000000000000000000000000000abc",
        asset="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC on mainnet as a stand-in
        max_amount_required="10000",  # 6-dec $0.01
        description="test premium insight",
        api_key="cdp-key-123",
    )
    base.update(overrides)
    return x.X402Config(**base)


def _b64_payload() -> str:
    payload = {
        "x402Version": 1,
        "accepted": {"scheme": "exact", "network": x.NETWORK_TESTNET},
        "payload": {
            "signature": "0xsig",
            "publicKey": "0xdeadbeef",
            "authorization": {"from": "0x1", "to": "0x2"},
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _patch_facilitator(monkeypatch, *, verify_resp, settle_resp) -> None:
    """Stub EvmX402Facilitator's httpx calls with a MockTransport."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/verify":
            return httpx.Response(200, json=verify_resp)
        if request.url.path == "/settle":
            return httpx.Response(200, json=settle_resp)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(x.httpx, "AsyncClient", _factory)


# ---- PaymentRequirements shape ------------------------------------


def test_build_payment_requirements_shape():
    cfg = _configured_cfg()
    req = x.build_payment_requirements(cfg, "https://api.kajota.test/coach/premium")
    assert req["scheme"] == "exact"
    assert req["network"] == x.NETWORK_TESTNET
    # XLayer emits BOTH the Coinbase-standard `maxAmountRequired` AND the
    # Casper-facilitator-compat `amount`, so the same body works either way.
    assert req["maxAmountRequired"] == "10000"
    assert req["amount"] == "10000"
    assert req["payTo"] == "0x0000000000000000000000000000000000000abc"
    assert req["asset"].startswith("0x")
    assert req["resource"].endswith("/coach/premium")
    for key in ("mimeType", "maxTimeoutSeconds", "extra", "description"):
        assert key in req


# ---- payload decoding ---------------------------------------------


def test_decode_payment_payload_base64():
    decoded = x._decode_payment_payload(_b64_payload())
    assert decoded["x402Version"] == 1
    assert decoded["accepted"]["scheme"] == "exact"
    assert decoded["payload"]["publicKey"] == "0xdeadbeef"


def test_decode_payment_payload_raw_json():
    raw = json.dumps({"scheme": "exact"})
    assert x._decode_payment_payload(raw)["scheme"] == "exact"


def test_read_payment_header_prefers_x_payment():
    req = _make_request({"X-PAYMENT": "aaa", "Payment-Signature": "bbb"})
    assert x._read_payment_header(req) == "aaa"
    req2 = _make_request({"Payment-Signature": "bbb"})
    assert x._read_payment_header(req2) == "bbb"


# ---- config resolution --------------------------------------------


def test_config_from_env_defaults(monkeypatch):
    for k in (
        "X402_FACILITATOR_URL",
        "X402_NETWORK",
        "X402_PAY_TO",
        "X402_ASSET",
        "X402_FACILITATOR_API_KEY",
        "X402_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    cfg = x.X402Config.from_env(description="d")
    # XLayer default facilitator is env-only — clean checkout means empty URL,
    # which is exactly the "not configured" state we want to fail-closed on.
    assert cfg.facilitator_url == ""
    assert cfg.network == x.NETWORK_TESTNET  # safe default: eip155:195
    assert cfg.configured is False  # no facilitator/payTo/asset → demo-stub


def test_config_extra_carries_erc20_domain(monkeypatch):
    # EIP-712 domain seeding needs `name` + `version` + `decimals` for the
    # wallet-side rendering of the price tag. XLayer defaults describe a
    # 6-decimal USDC/USDT-shaped stablecoin, not Casper's WCSPR.
    for k in ("X402_ASSET_NAME", "X402_ASSET_VERSION", "X402_ASSET_DECIMALS", "X402_ASSET_EXTRA"):
        monkeypatch.delenv(k, raising=False)
    cfg = x.X402Config.from_env(description="d")
    assert cfg.extra["version"]  # non-empty
    assert cfg.extra["name"] == "KaJota USD"  # our MockUSDC deployed on XLayer
    assert cfg.extra["decimals"] == "6"
    # And it lands in the built requirements.
    req = x.build_payment_requirements(cfg, "https://x/y")
    assert req["extra"]["version"] == "2"


def test_x402_version_defaults_to_1():
    # Coinbase CDP facilitator speaks v1 on EVM chains.
    assert x.X402_VERSION == 1


def test_config_api_key_falls_back_to_x402_api_key(monkeypatch):
    # No CSPR_CLOUD_API_KEY fallback on XLayer — the buildathon-specific env
    # only exists on Casper. XLayer accepts X402_FACILITATOR_API_KEY or its
    # alias X402_API_KEY, nothing else.
    monkeypatch.delenv("X402_FACILITATOR_API_KEY", raising=False)
    monkeypatch.setenv("X402_API_KEY", "shared-key")
    monkeypatch.setenv("X402_FACILITATOR_URL", "https://x402.example.com")
    monkeypatch.setenv("X402_PAY_TO", "0xabc")
    monkeypatch.setenv("X402_ASSET", "0xdef")
    cfg = x.X402Config.from_env(description="d")
    assert cfg.api_key == "shared-key"
    assert cfg.configured is True


# ---- require_payment gate -----------------------------------------


@pytest.mark.asyncio
async def test_unconfigured_returns_402_with_explanation():
    # XLayer's `configured` needs facilitator_url + payTo + asset (no api_key
    # required — some self-hosted facilitators don't check bearer). Missing
    # facilitator_url is the most common misconfig.
    cfg = _configured_cfg(facilitator_url="")
    req = _make_request({"X-PAYMENT": _b64_payload()})
    with pytest.raises(x.PaymentRequiredError) as ei:
        await x.require_payment(req, cfg)
    assert ei.value.response.status_code == 402
    body = json.loads(bytes(ei.value.response.body))
    assert "not fully configured" in body["error"]


@pytest.mark.asyncio
async def test_missing_header_returns_402_price_tag():
    cfg = _configured_cfg()
    req = _make_request()  # no payment header
    with pytest.raises(x.PaymentRequiredError) as ei:
        await x.require_payment(req, cfg)
    resp = ei.value.response
    assert resp.status_code == 402
    body = json.loads(bytes(resp.body))
    assert body["x402Version"] == 1
    assert body["accepts"][0]["scheme"] == "exact"
    assert body["accepts"][0]["network"] == "eip155:195"
    assert "X-PAYMENT" in body["error"]
    # Price tag mirrored into the header too.
    assert "PAYMENT-REQUIRED" in resp.headers


@pytest.mark.asyncio
async def test_malformed_header_returns_402():
    cfg = _configured_cfg()
    req = _make_request({"X-PAYMENT": "%%%not-base64-not-json%%%"})
    with pytest.raises(x.PaymentRequiredError) as ei:
        await x.require_payment(req, cfg)
    assert "malformed" in json.loads(bytes(ei.value.response.body))["error"]


@pytest.mark.asyncio
async def test_happy_path_verifies_and_settles(monkeypatch):
    cfg = _configured_cfg()
    _patch_facilitator(
        monkeypatch,
        verify_resp={"isValid": True, "payer": "0xpayer", "invalidReason": None},
        settle_resp={
            "success": True,
            "transaction": "0xdeadbeef0123456789",
            "network": x.NETWORK_TESTNET,
            "payer": "0xpayer",
        },
    )
    req = _make_request({"X-PAYMENT": _b64_payload()})
    result = await x.require_payment(req, cfg)
    assert result.success is True
    assert result.transaction == "0xdeadbeef0123456789"
    assert result.payer == "0xpayer"
    assert result.network == "eip155:195"
    # Settlement header round-trips as base64 JSON.
    decoded = json.loads(base64.b64decode(result.response_header()))
    assert decoded["transaction"] == "0xdeadbeef0123456789"
    assert decoded["network"] == "eip155:195"


@pytest.mark.asyncio
async def test_verify_failure_returns_402(monkeypatch):
    cfg = _configured_cfg()
    _patch_facilitator(
        monkeypatch,
        verify_resp={"isValid": False, "invalidReason": "bad signature", "payer": ""},
        settle_resp={"success": True},  # never reached
    )
    req = _make_request({"X-PAYMENT": _b64_payload()})
    with pytest.raises(x.PaymentRequiredError) as ei:
        await x.require_payment(req, cfg)
    assert "verification failed" in json.loads(bytes(ei.value.response.body))["error"]


@pytest.mark.asyncio
async def test_settle_failure_returns_402(monkeypatch):
    cfg = _configured_cfg()
    _patch_facilitator(
        monkeypatch,
        verify_resp={"isValid": True, "payer": "0xp", "invalidReason": None},
        settle_resp={"success": False, "errorReason": "insufficient balance"},
    )
    req = _make_request({"X-PAYMENT": _b64_payload()})
    with pytest.raises(x.PaymentRequiredError) as ei:
        await x.require_payment(req, cfg)
    assert "settlement failed" in json.loads(bytes(ei.value.response.body))["error"]
