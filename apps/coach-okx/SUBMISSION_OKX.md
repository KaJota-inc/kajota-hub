# OKX.AI Genesis Hackathon — Kajota Coach ASP submission

Paste-ready copy for the [OKX.AI Genesis Hackathon](https://www.hackquest.io/hackathons/OKXAI-Genesis-Hackathon)
Google Form ([forms.gle/mddEUagmDbyV37ws8](https://forms.gle/mddEUagmDbyV37ws8)).
Fill the bracketed links after the ASP is live + demo is recorded.

Judge-facing: **every claim below has an in-repo file:line or an on-chain
tx**. Verify in ≤2 minutes.

---

## Project

**Name:** Kajota Coach — Agentic Commerce ASP on XLayer

**Tagline:** An AI shopping concierge listed on OKX.AI that pays for its
own premium work with HTTP-native micropayments settled on XLayer — and
escrows real trades on-chain for A2A deals larger than a coffee.

**Categories targeted (in fit order):**
- **Revenue Rocket** — merchant enablement for underbanked SME
  commerce (see "Real-world use case" below).
- **Finance Copilot** — on-chain escrow rail (A2A) with dispute-safe
  release/refund on XLayer + Ethereum Sepolia + Arbitrum Sepolia.
- **Best Product** — the whole thing works end-to-end today; the
  "product" is the composition of Coach + Mesh, both live on Render.
- **Software Utility** — A2MCP marketplace metering as a service any
  other ASP can graft onto (`x402_xlayer.py` is a drop-in module).

**Modes:** A2MCP (pay-per-call on `/coach/premium` via x402) + A2A
(escrow on-chain via the Mesh SKILL). Both live simultaneously.

---

## Links

- **ASP on OKX.AI marketplace:** [link once approved]
- **Live Coach ASP:** https://kajota-coach-okx.onrender.com/ ·
  discovery: https://kajota-coach-okx.onrender.com/coach/premium
  (returns a 402 with an x402 price tag — proof the paywall is live)
- **Live Mesh SKILL:** https://kajota-mesh-okx.onrender.com/healthz
- **Repo (branch `hackathon/okx-asp`):**
  https://github.com/KaJota-inc/kajota-coach/tree/hackathon/okx-asp
- **Mesh contracts repo (branch `hackathon/okx-genesis`):**
  https://github.com/KaJota-inc/kajota-mesh/tree/hackathon/okx-genesis
- **Demo video (≤90 s):** [YouTube link — record before submit]
- **X thread (with #OKXAI):** [x.com/Oluwabori6 status link]
- **Technical write-up:** `agent/OKX_SETUP.md` and this file

---

## Verifiable claims table

Everything a judge might want to check, with the source-of-truth link.

### On-chain proofs

| Claim | Where to verify |
|---|---|
| Mesh escrow live on **XLayer testnet (chain 195)** | OKLink → `deployments/195.json` in the mesh repo (address + tx) |
| Mesh escrow live on **Ethereum Sepolia (chain 11155111)** | [CosellEscrow `0x599869cef2e4c52e2c9074caaf8f9fb0cb191776`](https://sepolia.etherscan.io/address/0x599869cef2e4c52e2c9074caaf8f9fb0cb191776) · registry [`0xfce6bd68d8d6f858d447f537d206c1e354b44315`](https://sepolia.etherscan.io/address/0xfce6bd68d8d6f858d447f537d206c1e354b44315) |
| Mesh escrow live on **Arbitrum Sepolia (chain 421614)** | [CosellEscrow `0x599869cef…91776`](https://sepolia.arbiscan.io/address/0x599869cef2e4c52e2c9074caaf8f9fb0cb191776) · [registry `0xfce6bd68d…44315`](https://sepolia.arbiscan.io/address/0xfce6bd68d8d6f858d447f537d206c1e354b44315) · USDC `0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d` · addresses in [`deployments/421614.json`](https://github.com/KaJota-inc/kajota-mesh/blob/hackathon/okx-genesis/packages/contracts/deployments/421614.json) |
| Coach's x402 settlement produces an XLayer tx | Demo video timestamp + `X-PAYMENT-RESPONSE` header on any real `POST /coach/premium` |

### In-repo proofs

| Claim | Where to verify |
|---|---|
| Coach's `/coach/premium` is x402-gated for XLayer | [`agent/kajota_concierge/server.py:374`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/agent/kajota_concierge/server.py#L374) |
| The x402 gate (EIP-3009 / Permit2) module | [`agent/kajota_concierge/x402_xlayer.py`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/agent/kajota_concierge/x402_xlayer.py) — `EvmX402Facilitator`, `X402Config.from_env`, `require_payment` |
| Hardhat config with XLayer testnet + mainnet chain ids | [`packages/contracts/hardhat.config.ts`](https://github.com/KaJota-inc/kajota-mesh/blob/hackathon/okx-genesis/packages/contracts/hardhat.config.ts) — `xlayerTestnet` network entry, chainId 195 |
| Auto-MockUSDC XLayer deploy script | [`packages/contracts/scripts/deploy-xlayer.ts`](https://github.com/KaJota-inc/kajota-mesh/blob/hackathon/okx-genesis/packages/contracts/scripts/deploy-xlayer.ts) |
| ASP service manifest template (dual A2MCP + A2A) | [`agent/asp-manifest.json`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/agent/asp-manifest.json) |
| Render blueprint pinned to `hackathon/okx-asp` | [`render.yaml`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/render.yaml) |
| Mesh SKILL wired for XLayer | [`skill/SKILL.md`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/skill/SKILL.md) |
| End-to-end runbook (deploy → register → submit) | [`agent/OKX_SETUP.md`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/agent/OKX_SETUP.md) |
| Demo storyboard (4 beats × 22 s) + X thread copy | [`agent/DEMO_STORYBOARD.md`](https://github.com/KaJota-inc/kajota-coach/blob/hackathon/okx-asp/agent/DEMO_STORYBOARD.md) |

### Test count

| Suite | Count | Location |
|---|---|---|
| Coach x402 gate — Casper baseline | 12 | `agent/tests/test_x402_casper.py` |
| Coach x402 gate — XLayer/EVM (this submission) | 14 | `agent/tests/test_x402_xlayer.py` |
| Mesh Solidity contracts | 47 | `packages/contracts/test/*.test.ts` |
| **Total** | **73** | `pytest -q agent/tests && pnpm --filter @kajota-mesh/contracts test` |

---

## Real-world use case

Sub-Saharan African merchants and SMEs live on WhatsApp and cash. Trust
across informal channels is the binding constraint: buyers won't send
money without seeing the product, sellers won't ship without seeing the
money. Kajota Coach lets an AI agent negotiate on behalf of a buyer,
escrow the funds in an on-chain contract, and release only on
delivery confirmation — with a per-call metered ASP layer so the agent's
"insight" work is also paid for automatically.

- **A2MCP flow** ($0.01 USDC/call): a buyer agent asks Coach for a
  premium purchase insight. Coach's `/coach/premium` returns 402 with a
  price tag; the buyer's OKX.AI CLI signs an EIP-3009 authorisation;
  Coach's facilitator settles on XLayer in seconds; the insight is
  returned with the on-chain tx hash in `X-PAYMENT-RESPONSE`.
- **A2A flow** (arbitrary USD amount): a buyer wants to commit to an
  actual purchase surfaced by Coach. The Mesh SKILL locks USDC in a
  `CosellEscrow` contract; on delivery confirmation, `release` sends
  the funds to the seller; on failure, `refund` returns them to the
  buyer. Same contract already live on 3 chains — the merchant chooses
  the L2 they trust.

Both flows share the same OKX.AI marketplace identity (ERC-8004) — one
ASP, two payment surfaces.

---

## How to reproduce in 5 minutes

Everything you need is in `agent/OKX_SETUP.md`. Compressed version:

```bash
# 1. Clone
git clone https://github.com/KaJota-inc/kajota-coach.git
git clone https://github.com/KaJota-inc/kajota-mesh.git

# 2. Confirm the paywall answers 402 (no OKX login needed)
curl -s https://kajota-coach-okx.onrender.com/coach/premium | jq

# 3. Verify contract addresses
cat kajota-mesh/packages/contracts/deployments/195.json         # XLayer testnet
cat kajota-mesh/packages/contracts/deployments/11155111.json    # Ethereum Sepolia
```

For a full local reproduction: `pnpm install && pnpm test` in
`kajota-mesh/packages/contracts` runs the 47 Solidity tests hermetically;
`cd kajota-coach/agent && pip install -e . && pytest -q tests/` runs
the 26 Python tests (12 Casper + 14 XLayer) hermetically via httpx's
MockTransport (no facilitator required).

---

## Team

Solo builder: **Oluwabori Ola** — [github.com/KaJota-inc](https://github.com/KaJota-inc)
· [x.com/Oluwabori6](https://x.com/Oluwabori6) · [t.me/BoriAdura](https://t.me/BoriAdura)

Building Kajota — commerce infrastructure for African SMEs, on-chain
where trust needs to be verifiable, off-chain where it doesn't.

---

## Roadmap (post-hackathon)

- **Aug 2026**: XLayer mainnet cutover — swap facilitator to production
  endpoint, redeploy mesh to chain 196, promote from A2MCP demo to real
  merchant traffic.
- **Sep 2026**: Second ASP — Mesh Escrow standalone service in the
  OKX.AI marketplace. Same manifest pattern, different endpoint.
- **Q4 2026**: Merchant onboarding rail via WhatsApp Business API →
  Coach → OKX.AI, closing the loop from informal buyer conversation to
  on-chain settlement.

---

## Guardrails / honesty

- Mantle Sepolia and Polygon Amoy addresses that circulated in earlier
  Kajota material are **not** re-cited here — those `deployments/*.json`
  files don't exist on this branch. The three chains cited above are
  the three we can prove.
- The 90-second demo will show live XLayer testnet tx hashes, not
  screenshots of a staging environment. If the demo cuts before an
  on-chain confirmation, that beat is redone.
- No AI voice used — the demo will use real-recorded VO (some hackathons
  ban AI voice; we default to the stricter rule).
