# DoraHacks BUIDL — KaJota Coach × Casper

Paste-ready copy for the [Casper Agentic Buildathon 2026](https://dorahacks.io/hackathon/casper-agentic-buildathon)
submission. Fill the bracketed links at submission time.

---

**Project name:** KaJota Coach — Agentic Commerce on Casper

**Tagline:** An AI shopping concierge that pays for its own premium work with
HTTP-native micropayments settled on Casper.

**Tracks:** Agentic AI · DeFi & Payments

**Links:**
- Repo (branch `hackathon/casper`): https://github.com/KaJota-inc/kajota-coach/tree/hackathon/casper
- PR (the full diff for this Buildathon): https://github.com/KaJota-inc/kajota-coach/pull/3
- Demo video: [YouTube link — record before submit]
- Write-up: `agent/CASPER.md` in the repo

## What's new for this Buildathon

KaJota Coach is our existing open-source AI shopping agent. **Everything that
makes it a Casper project was built new for this Buildathon** and lives on the
`hackathon/casper` branch (see the PR diff):

- a server-side **x402 v2 protocol** implementation for Casper (`x402_casper.py`),
- our own **deployed CEP-18** contract with `transfer_with_authorization`
  (`deploy_cep18x402.mjs` → KaJota USD on testnet),
- the **client signer + facilitator settlement** path (`x402_client.mjs`,
  `settle_once.mjs`, signer bridge),
- the **Casper MCP** agent integration, and a **mobile Premium screen** for the
  pay-per-call flow.

We're upfront that the base agent pre-exists; the Casper integration — the part
this Buildathon is about — is original and new, and it settles on-chain today.

## On-chain proof (Casper Testnet)

Everything below is live and verifiable on cspr.live:

| What | Value |
|---|---|
| **Our CEP-18 contract** (KaJota USD, with `transfer_with_authorization`) | package `354ca0ad7ef8c97a02b195a1f39e96908fd3bf20d6ec4255850d05f1784fb404` |
| **Contract deploy tx** | [`df084784…`](https://testnet.cspr.live/transaction/df0847848800502b1b6919c1ad9a2dc0845c309006382b21ef8ad759d7c4171a) |
| **x402 settlement tx** (agent micropayment — a real `transfer_with_authorization`) | [`88c4153e…`](https://testnet.cspr.live/transaction/88c4153e211011915b7b7bc2af718ada2b506266512701a7488a80f77a58b4a3) — processed, block 8394190 |

The settlement's gas was paid by Casper's sponsored x402 **feePayer** — the
agent moved value without holding native gas, exactly the x402 promise.

---

## The problem

AI agents can reason, but they can't *transact*. The moment an agent needs a
paid resource — a premium analysis, another agent's API, a data feed — it hits
a human wall: sign up, get an API key, attach a card, wait for approval. That
breaks autonomy. Agents need to pay the way they call: per request, instantly,
with cryptographic proof and no human in the loop.

## What we built

KaJota Coach is an agentic shopping concierge (Gemini + Google ADK, with
MongoDB and Fetch reached over MCP). For the buildathon we made it a
**Casper-native economic actor**, two ways:

1. **It charges for its own premium work.** `POST /coach/premium` runs a deep
   purchase-insight turn (spend trends, wishlist price-drop opportunities, a
   grounded next-buy recommendation) behind an **x402 paywall**. An agent that
   wants it gets a `402` with a price tag, signs a CEP-18
   `transfer_with_authorization`, and the **CSPR.cloud x402 Facilitator**
   settles it on Casper — no account, no key, no human. The response carries
   the on-chain deploy hash as proof.

2. **It reads Casper in natural language.** The Casper MCP server is bolted on
   as a third MCP partner, so the Coach can answer "what's my CSPR balance?" or
   "did that payment settle?" by querying the chain directly — the same
   MCP-as-architecture pattern as its MongoDB and Fetch partners.

## Why it's real, not a mock

We built against the **production** facilitator and verified the wire protocol
live (Jun 27, 2026), correcting several things the public examples get wrong:

- The facilitator runs **x402 v2** and reads the price field as `amount` (not
  the x402-standard `maxAmountRequired`).
- `payTo` is a "00"-prefixed **account-hash**; the asset must implement
  **`transfer_with_authorization`** (we deployed our own — KaJota USD); and
  `extra.version` (the EIP-712 domain) is mandatory.

And it doesn't just pass `/verify` — **it settled for real.** We deployed our
own CEP-18, signed a `transfer_with_authorization`, and the production
facilitator settled it on Casper (tx `88c4153e…`, processed on-chain). The
full agent-payment loop runs against Casper's real infrastructure, not a mock.

## Tech stack

- **Casper AI Toolkit** — x402 Facilitator (CSPR.cloud), Casper MCP server,
  CEP-18 (`transfer_with_authorization`) on testnet
- **Agent** — Google ADK + Gemini, FastAPI, Model Context Protocol
- **Payments** — x402 v2 (`exact` scheme, `casper:casper-test`), settled on Casper
- 14 unit tests; isolated server-side x402 module in pure Python

## Ecosystem contribution & long-term impact

Casper's strategic bet right now is its **AI Toolkit** — x402, the MCP server,
Odra, CSPR.cloud. Most projects use one piece. **This project wires the whole
stack together and settles on-chain**, so it doubles as a **public reference
implementation** other Casper builders can copy:

- a **working server-side x402 v2** in Python (no official Python SDK existed —
  we built it and documented every wire-format correction we found against the
  live facilitator: `amount` vs `maxAmountRequired`, v2 envelope, account-hash
  `payTo`, `transfer_with_authorization` assets, mandatory `extra.version`);
- an **end-to-end deploy → sign → settle** flow with runnable scripts and a
  one-command demo (`npm run demo`);
- the **Casper MCP** composed alongside other MCP partners in a real agent.

Every finding is in `CASPER.md` and the code is MIT-licensed — the kind of
"how do I actually ship x402 on Casper?" answer the ecosystem needs to grow
agentic-payments adoption. That's the long-term impact: not one app, but a
template that lowers the barrier for the next hundred Casper AI builders.

## Roadmap (real project, not a hackathon throwaway)

KaJota is a live product (AI commerce for African micro-merchants), not a demo.
Concrete next steps on Casper:

1. **Mainnet x402** — flip the network to `casper:casper` and settle premium
   agent calls in production against a mainnet CEP-18.
2. **Agent-to-agent commerce** — KaJota agents paying *each other* per call
   (the Coach paying a pricing agent, a logistics agent) — an x402 mesh.
3. **Stablecoin settlement** — swap KaJota USD for a Casper-native stablecoin so
   merchant payouts settle in a stable unit, tying x402 to real DeFi/RWA flows.
4. **Publish the reference** — extract the Python x402 layer into a standalone
   `casper-x402-python` package for the ecosystem.

Links, socials, and the live product: [KaJota — add kajota.io / X / repo org
links at submission time].
