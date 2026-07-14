"""Unit tests for the Casper x402 paywall (``x402_casper``).

These deliberately exercise the module in isolation — it imports neither the
ADK agent nor google-adk, so the suite runs with just fastapi + httpx +
pytest. The facilitator HTTP calls are stubbed via httpx's MockTransport so
the tests are hermetic (no network, no sponsored key needed).
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from starlette.requests import Request

from kajota_concierge import x402_casper as x


# ---- helpers ------------------------------------------------------


def _make_request(headers: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request for ``require_payment``.

    require_payment only touches ``request.url`` and ``request.headers``, so a
    bare ASGI scope is enough.
    """
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
        facilitator_url="https://x402-facilitator.cspr.cloud",
        network=x.NETWORK_TESTNET,
        pay_to="account-hash-0xdeadbeef",
        asset="hash-cep18-usdc",
        max_amount_required="1000",
        description="test premium insight",
        api_key="sponsored-key-123",
    )
    base.update(overrides)
    return x.X402Config(**base)


def _b64_payload() -> str:
    payload = {
        "x402Version": 2,
        "accepted": {"scheme": "exact", "network": x.NETWORK_TESTNET},
        "payload": {
            "signature": "0xsig",
            "publicKey": "02deadbeef",
            "authorization": {"from": "00a", "to": "00b"},
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _patch_facilitator(monkeypatch, *, verify_resp, settle_resp) -> None:
    """Stub CasperX402Facilitator's httpx calls with a MockTransport."""

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
    # Casper facilitator reads `amount`, not the x402-standard `maxAmountRequired`.
    assert req["amount"] == "1000"
    assert "maxAmountRequired" not in req
    assert req["payTo"] == "account-hash-0xdeadbeef"
    assert req["asset"] == "hash-cep18-usdc"
    assert req["resource"].endswith("/coach/premium")
    # Every x402 field a facilitator expects must be present.
    for key in ("mimeType", "maxTimeoutSeconds", "extra", "description"):
        assert key in req


# ---- payload decoding ---------------------------------------------


def test_decode_payment_payload_base64():
    decoded = x._decode_payment_payload(_b64_payload())
    # v2 payload nests the agreed requirements under `accepted`.
    assert decoded["x402Version"] == 2
    assert decoded["accepted"]["scheme"] == "exact"
    assert decoded["payload"]["publicKey"] == "02deadbeef"


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
        "CSPR_CLOUD_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    cfg = x.X402Config.from_env(description="d")
    assert cfg.facilitator_url == x.DEFAULT_FACILITATOR_URL
    assert cfg.network == x.NETWORK_TESTNET  # safe default
    assert cfg.configured is False  # no payTo/asset/key → demo-stub mode


def test_config_extra_has_required_version(monkeypatch):
    # The facilitator rejects a payment whose requirements.extra lacks a
    # non-empty `version` (it seeds the EIP-712 domain). from_env must always
    # produce one, plus WCSPR-style name/decimals; X402_FEE_PAYER flows in.
    for k in ("X402_ASSET_NAME", "X402_ASSET_VERSION", "X402_ASSET_DECIMALS", "X402_ASSET_EXTRA"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("X402_FEE_PAYER", "81d557c9deadbeef")
    cfg = x.X402Config.from_env(description="d")
    assert cfg.extra["version"]  # non-empty
    assert cfg.extra["name"] == "WCSPR"
    assert cfg.extra["decimals"] == "9"
    assert cfg.extra["feePayer"] == "81d557c9deadbeef"
    # And it lands in the built requirements.
    req = x.build_payment_requirements(cfg, "https://x/y")
    assert req["extra"]["version"]


def test_x402_version_defaults_to_2():
    assert x.X402_VERSION == 2


def test_config_api_key_falls_back_to_cspr_cloud(monkeypatch):
    monkeypatch.delenv("X402_FACILITATOR_API_KEY", raising=False)
    monkeypatch.delenv("X402_API_KEY", raising=False)
    monkeypatch.setenv("CSPR_CLOUD_API_KEY", "shared-key")
    monkeypatch.setenv("X402_PAY_TO", "p")
    monkeypatch.setenv("X402_ASSET", "a")
    cfg = x.X402Config.from_env(description="d")
    assert cfg.api_key == "shared-key"
    assert cfg.configured is True


# ---- require_payment gate -----------------------------------------


@pytest.mark.asyncio
async def test_unconfigured_returns_402_with_explanation():
    cfg = _configured_cfg(api_key="")  # missing sponsored key
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
    assert body["x402Version"] == 2
    assert body["accepts"][0]["scheme"] == "exact"
    assert "X-PAYMENT" in body["error"]
    # Price tag mirrored into the header too.
    assert "PAYMENT-REQUIRED" in resp.headers


@pytest.mark.asyncio
async def test_malformed_header_returns_402(monkeypatch):
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
        verify_resp={"isValid": True, "payer": "account-hash-payer", "invalidReason": None},
        settle_resp={
            "success": True,
            "transaction": "deploy-hash-abc123",
            "network": x.NETWORK_TESTNET,
            "payer": "account-hash-payer",
        },
    )
    req = _make_request({"X-PAYMENT": _b64_payload()})
    result = await x.require_payment(req, cfg)
    assert result.success is True
    assert result.transaction == "deploy-hash-abc123"
    assert result.payer == "account-hash-payer"
    # The settlement header round-trips as base64 JSON.
    decoded = json.loads(base64.b64decode(result.response_header()))
    assert decoded["transaction"] == "deploy-hash-abc123"


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
        verify_resp={"isValid": True, "payer": "p", "invalidReason": None},
        settle_resp={"success": False, "errorReason": "insufficient balance"},
    )
    req = _make_request({"X-PAYMENT": _b64_payload()})
    with pytest.raises(x.PaymentRequiredError) as ei:
        await x.require_payment(req, cfg)
    assert "settlement failed" in json.loads(bytes(ei.value.response.body))["error"]
