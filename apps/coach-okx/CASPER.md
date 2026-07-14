# KaJota Coach × Casper — Agentic Buildathon 2026

**Snap a deal, settle it on Casper.** KaJota Coach is an agentic shopping
concierge (Gemini + Google ADK + MongoDB MCP). This branch makes it a
**Casper-native economic actor**: it can *read* the Casper chain over MCP and
*charge for its own premium work* with HTTP-native x402 micropayments settled
on Casper.

> Buildathon: [Casper Agentic Buildathon 2026](https://dorahacks.io/hackathon/casper-agentic-buildathon)
> · $150K · submission deadline **Jul 1, 2026** · tracks: **Agentic AI**, **DeFi & Payments**.

---

## What we added (and why it's lean)

The Coach already speaks **MCP** (MongoDB + Fetch) and is already a **FastAPI**
service. Casper's AI Toolkit gives us two drop-in surfaces, so the whole
integration is *additive* — no rewrite:

| Track | Feature | Casper piece used | Where |
|---|---|---|---|
| **Agentic AI** | Agent reads on-chain state in natural language (balances, deploys, transfers, contracts) | [`casper-mcp`](https://github.com/msanlisavas/casper-mcp) as a 3rd `McpToolset` | `kajota_concierge/agent.py` |
| **DeFi & Payments** | `POST /coach/premium` is pay-per-call, settled on Casper | [CSPR.cloud x402 Facilitator](https://docs.cspr.cloud/x402-facilitator-api/reference) (`/verify` + `/settle`) | `kajota_concierge/x402_casper.py` + `server.py` |

Why we hand-rolled the x402 server side: the only official x402 **server** SDKs
are Node (`@make-software/casper-x402`) and Go. The Coach is Python, and the
facilitator is a plain HTTP service — so we speak that HTTP directly (`/verify`,
`/settle`) rather than bolt on a Node sidecar. The implementation is a faithful
port of the standard x402 envelope (`exact` scheme, `casper:*` CAIP-2 family).

---

## The x402 flow (HTTP 402, revived for agents)

```
Agent                         KaJota Coach (FastAPI)            CSPR.cloud Facilitator        Casper
  │  POST /coach/premium  ───────▶  │                                  │                         │
  │                                 │  no X-PAYMENT → 402 + price tag   │                         │
  │  ◀── 402 { x402Version:2, accepts:[ {scheme:"exact",               │                         │
  │           network:"casper:casper-test", amount, payTo, asset,       │                         │
  │           extra:{name,version,decimals,feePayer}} ] }               │                         │
  │                                 │                                  │                         │
  │  sign EIP-712 transfer_with_authorization over the CEP-18 token    │                         │
  │  POST /coach/premium  ─────────▶│                                  │                         │
  │   X-PAYMENT: <base64 payload>   │  POST /verify {payload,reqs} ───▶│  sig + replay check     │
  │                                 │  ◀── { isValid:true }            │                         │
  │                                 │  POST /settle {payload,reqs} ───▶│  transfer_with_auth ───▶│  CEP-18
  │                                 │  ◀── { success:true, transaction:<deploy hash> }           │
  │                                 │  run premium agent turn          │                         │
  │  ◀── 200 { response, settlement:{ transaction, payer, settled } }  │                         │
  │       X-PAYMENT-RESPONSE: <base64 receipt>                          │                         │
```

The premium turn is a real ADK deep-dive (spend trend + wishlist price-drop
opportunities + a grounded next-buy recommendation), so the micropayment buys
genuine agent work — not a toy gate.

---

## Run the demo

**One command** (from the repo root) brings up the whole local stack — agent
(`:8080`) + signer bridge (`:4040`) + Metro (`:8088`) — with health checks and
clean Ctrl-C shutdown:

```sh
export CLIENT_PRIVATE_KEY_PATH=./agent/scripts/payer.pem   # for one-tap pay
npm run demo
# then, in another terminal:  npm run ios   (open the app, tap Premium Insight)
```

It loads `agent/.env.casper`, skips the bridge gracefully if no payer key is
set (the app still shows the live 402), and refuses to start if the Metro port
is held by a stale server from another project. The manual steps below are the
same stack, broken out.

> **Protocol note (verified live, Jun 27, 2026).** The CSPR.cloud facilitator
> runs **x402 v2** and reads the price field as **`amount`** (not the x402
> standard `maxAmountRequired`). The full v2 envelope this server emits was
> validated against the production `/verify` — every field is accepted; only a
> real signature is left to the client. `/supported` returns schemes, networks,
> and the sponsored `feePayer` — **not** assets.

### 0. Prereqs (one-time)
- **Sponsored key** — the buildathon issues a CSPR.cloud facilitator key (free
  on-chain tx). Sent as a raw `Authorization` header (no `Bearer`).
- **Casper account + test CSPR** — create one in Casper Wallet, fund it at the
  faucet <https://testnet.cspr.live/tools/faucet> (5,000 test CSPR, one-time).
  `X402_PAY_TO` is that account's **"00"-prefixed account hash**, not the public
  key (the facilitator rejects a raw pubkey).
- **feePayer** — the facilitator sponsors gas; read its account from
  `/supported`:
  ```sh
  export X402_FACILITATOR_API_KEY=<sponsored-key>
  python scripts/x402_demo.py --supported     # prints networks + feePayer
  ```
- **Payment asset** — a CEP-18 token (package hash) that implements
  `transfer_with_authorization`. A plain CEP-18 won't settle; use the
  buildathon's WCSPR-with-authorization or deploy one (Odra). This is the
  merchant's choice, set as `X402_ASSET`.

### 1. Configure
```sh
cd agent
cp .env.casper.example .env.casper
# fill X402_PAY_TO, X402_ASSET (from --supported), X402_FACILITATOR_API_KEY;
# set CASPER_MCP_ENABLED=1 for the MCP demo
set -a; . .env.casper; set +a
```

### 2. Boot the agent
```sh
pip install -e .
kajota-agent          # FastAPI on :8080
```

### 3. Hit the paywall (watch the 402 → pay → 200 dance)

The unpaid probe needs no key — `scripts/x402_demo.py` does it for real and
prints the decoded Casper price tag:

```sh
python scripts/x402_demo.py --url http://localhost:8080
# → POST .../coach/premium  (no payment)
# ← HTTP 402 Payment Required
#     accepts[0]: scheme=exact  network=casper:casper-test  amount=1000000
#                 asset=<cep18>  payTo=<merchant>  resource=.../coach/premium
#   …then prints the PaymentPayload skeleton a signer fills in.
```

Or with plain curl:
```sh
curl -i -X POST localhost:8080/coach/premium -H 'content-type: application/json' -d '{}'
#   HTTP/1.1 402 Payment Required
#   PAYMENT-REQUIRED: <base64 requirements>
```

To complete a **real on-chain settlement**, use the Node client signer
(`scripts/x402_client.mjs`). It reuses Casper's audited
`@make-software/casper-x402` + `casper-js-sdk` to sign the EIP-712
`transfer_with_authorization`, so `wrapFetchWithPayment` does the whole
402 → sign → retry automatically:

```sh
cd scripts && npm install
export CLIENT_PRIVATE_KEY_PATH=./payer.pem   # payer key; account must hold Wrapped CSPR
export CLIENT_KEY_ALGO=secp256k1
export SERVER_URL=http://localhost:8080
node x402_client.mjs
# 🌐 POST .../coach/premium  (will pay on 402)
# ✅ HTTP 200
# 💰 On-chain settlement:  network=casper:casper-test  deploy hash=<...>  payer=<...>
```

> **Why the signer is Node, not Python.** The server side (this repo) — the
> 402 price tag, then `/verify` + `/settle` against the Casper facilitator — is
> what the payments track scores, and it's pure Python, validated live. The
> client *signing* step is secp256k1 EIP-712 over Casper's custom domain;
> reimplementing that crypto in Python would be unjustified risk, so the client
> reuses Casper's official library. `scripts/x402_demo.py --payment <b64>` also
> accepts a pre-signed payload if you'd rather sign another way (CSPR.click, Go).

### 4. Agent reads Casper over MCP
With `CASPER_MCP_ENABLED=1` (Docker required):
```sh
curl -X POST localhost:8080/chat -H 'content-type: application/json' \
  -d '{"message":"What is the CSPR balance of account <hash>, and did deploy <hash> settle?"}'
# → the agent calls casper-mcp tools and reports real testnet state
```

---

## Tests

The paywall module is decoupled from the ADK agent, so it tests with a minimal
env (no google-adk, no Mongo, no network — facilitator calls are mocked):

```sh
python3.11 -m venv .venv && . .venv/bin/activate
pip install fastapi httpx pytest pytest-asyncio
PYTHONPATH=. pytest tests/test_x402_casper.py -q   # 12 passed
```

Covers: 402 price-tag shape, header parsing (`X-PAYMENT` / `Payment-Signature`),
base64 + raw payload decode, unconfigured fail-closed, verify-failure → 402,
settle-failure → 402, and the happy verify→settle→receipt path.

---

## Files

```
agent/kajota_concierge/x402_casper.py   # x402 server protocol + facilitator client (new)
agent/kajota_concierge/server.py        # POST /coach/premium + 402 handler (extended)
agent/kajota_concierge/agent.py         # gated casper-mcp toolset + on-chain rules (extended)
agent/kajota_concierge/__init__.py      # lazy root_agent so paywall imports light (changed)
agent/tests/test_x402_casper.py         # 12 unit tests (new)
agent/.env.casper.example               # Casper config template (new)
```

## Submission mapping

- **Agentic AI** — the Coach autonomously discovers Casper capabilities via MCP
  and reasons over real on-chain state; it acts, it doesn't just chat.
- **DeFi & Payments** — agent-to-agent micropayments: the Coach charges for
  premium work and settles a CEP-18 transfer on Casper per request, no account,
  no API key, no human in the loop — the x402 thesis, in production shape.
