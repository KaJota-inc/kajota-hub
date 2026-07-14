# Circle Developer Grants — Kajota Witness proposal

**Draft — Jul 5, 2026.** Paste-ready copy for [circle.questbook.app](https://circle.questbook.app/) Circle 2026 Cohort 2. Assumes fields close to the marketing page: business details, Circle/Arc integrations, product roadmap, proposed grant milestones.

---

## Project name

**Kajota Witness — Trustless dispute settlement for stablecoin commerce on Arc**

## Tagline (one-liner)

An on-chain AI jury that lets any Arc-based commerce app settle P2P and merchant disputes in USDC — encrypted evidence on 0G, verdict + slashable USDC bond on Arc — so agents, marketplaces, and payment rails can move USDC with a neutral, code-verified appeal path built in.

## What we've built (evidence, not vision)

Everything below is live and verifiable on public infrastructure today:

| Component | Live artifact |
|---|---|
| **`BondedWitnessAnchor` on Arc Testnet** | [`0x9AB71BAA…56b2`](https://testnet.arcscan.app/address/0x9AB71BAA32d91661aA6c35dFdba7F68c030456b2) — deploy tx [`0x8343a88c…8e28d`](https://testnet.arcscan.app/tx/0x8343a88ce621a29f7978476b0dbc7b9855d5a126b1b52cdba3c383c30b8be28d) |
| **`WitnessAnchor` on 0G Galileo** (v1 without bond) | [`0x2f1D3a88…cEC94`](https://chainscan-galileo.0g.ai/address/0x2f1D3a881cfbeA01Cf55f3cAd125aA32Bf8cEC94) |
| **Live server + `/verify` cross-check** | https://kajota-witness.onrender.com/verify |
| **Sample settled verdict** (paste into `/verify` for 4-way green) | `0xa9183d1a…92e5fb` |
| **Kajota Coach — agentic commerce assistant (production Render)** | https://kajota-concierge-agent.onrender.com/ (integration with Witness merged in `kajota-coach#2`) |
| **Public repo** (MIT) | https://github.com/KaJota-inc/kajota-witness |
| **Zero Cup demo video** (84s) | https://youtu.be/qlw1HUo6qwo |

**Shipped credentials for the "exceptional team" bar:**
- Submitted to 0G Zero Cup Round 1 (Group Stage cut). Full public repo, live URL, on-chain contract, integrated companion agent.
- 3 Kajota production surfaces on Render / Vercel: **Coach** (Google ADK + Gemini + MongoDB MCP + Casper x402 settlement), **Witness** (this proposal), **Pulse** (analytics for African micro-commerce).
- Deployed Casper CEP-18 (KaJota USD) with `transfer_with_authorization`, real x402 settlement live on Casper Testnet ([Casper Buildathon submission](https://github.com/KaJota-inc/kajota-coach/tree/hackathon/casper)).
- 47/47 Solidity tests green across the Mesh escrow stack (4 contracts, Ethereum Sepolia + Mantle Sepolia deployed).

## What the Circle grant funds

Three milestones, each paid on delivery. Amounts are our proposed USDC per milestone — happy to right-size during Circle's milestone-design step.

### Milestone 1 — Arc Mainnet BondedWitnessAnchor + Client SDK

**Deliverable:** BondedWitnessAnchor.sol deployed on **Arc Mainnet** (when Arc mainnet launches), including:

- `fileDispute(disputeId)` — filer stakes `BOND_AMOUNT` USDC via `IERC20.transferFrom` (real Circle USDC on Arc, not a mock).
- `anchor(disputeId, verdictRoot, ruling, confidenceBps)` — settles bond per ruling: `refund_buyer` returns to filer, `release_to_seller` slashes to treasury, `split_50_50` returns half, `escalate_to_human` returns to filer.
- **Permit2 integration** — one-signature approval for the bond stake, bringing UX to par with the rest of the Circle stack.
- TypeScript SDK (npm: `@kajota/witness-sdk`) with typed `fileDispute` / `anchor` / `getVerdict` methods so Circle Developer Platform users can drop dispute-settlement into any Arc app in ~10 lines.

**Success criteria:** 100 successful mainnet disputes settled from ≥3 independent test integrators, published SDK on npm, migration guide in docs.

**Proposed USDC:** *TBD during milestone-design (indicative: 5,000 USDC)*

### Milestone 2 — CCTP V2 pay-in bridge + StableFX FX-in bridge

**Deliverable:** buyer pay-in flows for Kajota Coach (agentic commerce) using Circle's cross-chain USDC + FX rails:

- **CCTP V2 integration** — buyer deposits USDC on Ethereum / Base / Polygon → auto-attests to Arc via `TokenMessengerV2` at [`0x8FE6B999…542DAA`](https://testnet.arcscan.app/address/0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA) → seller receives on Arc without holding a bridge intent.
- **StableFX FxEscrow integration** at [`0x867650F5…C9a9f8`](https://testnet.arcscan.app/address/0x867650F5eAe8df91445971f14d89fd84F0C9a9f8) — buyer holds NGN or another local stablecoin, quote-and-settle path lands USDC on the seller's Arc address. Cross-currency P2P for African micro-commerce.
- End-to-end demo: African seller lists a product on Coach → buyer in EU pays in EURC → CCTP bridges → StableFX converts → Arc USDC lands → Coach ships the product → any dispute goes to BondedWitnessAnchor.

**Success criteria:** 3 corridors live (NGN↔USDC, EURC↔USDC, brICK↔USDC), 10 successful live cross-corridor settlements, tutorial published.

**Proposed USDC:** *TBD (indicative: 8,000 USDC)*

### Milestone 3 — Ecosystem impact: "Witness as a Service" for Circle grantees

**Deliverable:** enable *other* Arc/Circle projects to use Witness as an out-of-the-box dispute layer with zero infrastructure of their own:

- Hosted multi-tenant Witness runtime — any Arc project can call `POST /dispute` with their own contract address, evidence CIDs, and get back an anchored verdict on Arc.
- REST + gRPC + WebSocket APIs for real-time dispute state.
- Circle grantee onboarding kit — 5 example integrations (e.g. Hurupay P2P disputes, Blockradar chargeback flow, Kajota Coach commerce, one lending grantee, one prediction market grantee).
- Public status page + on-chain dashboard.

**Success criteria:** 10 Arc projects integrated via API, 500 verdicts anchored on Arc Mainnet across those integrators in the first 90 days post-milestone.

**Proposed USDC:** *TBD (indicative: 12,000 USDC)*

**Total indicative ask: 25,000 USDC** across 3 milestones — right-size as Circle prefers.

## Alignment against Circle's 7 focus areas

| Use case | Kajota Witness role |
|---|---|
| **Agentic economic activity** | ★ Primary — AI jury (3 LLM jurors + judge) settles disputes when agents can't agree, without a human in the loop |
| **Peer-to-peer payments** | ★ Primary — bonded USDC dispute rail lets any P2P settle its own conflict without escalation to a centralized appeal |
| **Stablecoin FX** | Secondary — StableFX integration in Milestone 2 lands NGN/EURC/USD sellers with USDC in-flow |
| **Treasury management** | Adjacent — verdict bonds accumulating to treasury address create programmable USDC reserves |
| **Prediction markets** | Adjacent — the AI-jury settlement primitive generalizes to prediction-market outcome resolution |
| **Onchain lending** | Not core, but the `ScoreAttestation` credit-scoring anchor (Kajota Trade, deployed Polygon Amoy) is portable to Arc |

## Circle & Arc integrations (checklist)

- [x] **USDC** — Arc's native gas + our contract's bond asset. Testnet USDC `0x3600…0000` already integrated. Mainnet Circle USDC to swap in Milestone 1.
- [ ] **CCTP V2** — Milestone 2. Contract identified: `0x8FE6B999…542DAA` on Arc Testnet (domain 26).
- [ ] **StableFX FxEscrow** — Milestone 2. Contract identified: `0x867650F5…C9a9f8` on Arc Testnet.
- [ ] **Gateway Wallet** — investigating for Milestone 3 (optional embedded-wallet for judges / auditors of on-chain verdicts).
- [ ] **Nanopayments** — evaluate for the settlement-fee flow at the bond-slash step.

## Team

Kajota is a solo-founded but multi-repo African fintech agent stack:

- **Founder / engineer:** Oluwabori Aduragbemi Ola ([@bori7](https://github.com/bori7)) — Lagos, Nigeria.
- **Track record:** Casper Buildathon (real x402 settlement + own CEP-18), 0G Zero Cup (Witness Group Stage submission), Mantle Turing Test P2 (Rapid Agent, shipped), Rapid Agent submission (Google Cloud Rapid Agent Hackathon, Jun 11).
- **Shipping cadence:** 12 production commits in 52 wall-clock hours during 0G Zero Cup weekend, including deployed contract + live URL + integrated companion agent.
- **Domain:** African micro-commerce fintech — the exact intersection of "who needs stablecoin dispute rails" (informal cross-border P2P) and "who doesn't have them today" (WhatsApp escrow + Instagram DMs + zero appeal path).

## Traction

- 0G Zero Cup Round 1 (Group Stage) submission accepted — [see Group Stage bracket](https://0g.ai/arena/h/zero-cup/draw).
- Casper Buildathon Jul 7 submission in preparation — real on-chain x402 settlement live.
- Kajota Coach production agent [`kajota-concierge-agent.onrender.com`](https://kajota-concierge-agent.onrender.com) serves ~100 test users / mo.
- 3 hackathon-branch integration lines active: Casper (`hackathon/casper`), Witness (`feat/witness-memory-integration` MERGED), Ignyte (`hackathon/ignyte`).

## Roadmap post-grant

**Q3 2026 (grant period):**
- M1: Arc Mainnet BondedWitnessAnchor + SDK
- M2: CCTP V2 + StableFX buyer pay-in bridge (live in Kajota Coach)
- M3: Witness-as-a-Service for other Arc grantees

**Q4 2026:**
- Formal audit of BondedWitnessAnchor (Trail of Bits or similar)
- Enterprise integrations with 2–3 Nigerian escrow-style fintechs (existing warm intros via Kajota Coach usage)
- Regulatory frame published: how AI-jury verdicts hold up under existing consumer-protection laws in Nigeria + Kenya

**H1 2027:**
- Circle Wallets integration for embedded-wallet dispute filing
- Nanopayments-based dispute filing fee (0.10 USDC per filed dispute → prevents griefing, funds Witness treasury)

## Revenue model

Two lines, both USDC-denominated:

1. **Bond slashes** — losing filers forfeit `BOND_AMOUNT` USDC to treasury; Kajota takes 20% of slash volume as protocol revenue.
2. **API access** — Witness-as-a-Service (M3) charges 0.05 USDC per anchored verdict for hosted-runtime users.

**Scalability:** Arc handles ~5000 TPS on paper; even at 1% of that on Witness anchoring, we settle ~50 disputes/sec — orders of magnitude above realistic near-term demand.

## Why us, why now

**Why Witness is the right primitive:** every stablecoin app that touches P2P will eventually face disputes. Today they either (a) reverse via a centralized authority (defeats the point) or (b) don't reverse at all (users lose money and abandon the rail). A cheap, code-verified, on-chain appeal path with a slashable filer bond makes stablecoin-native disputes possible for the first time.

**Why Kajota is the right team:** we already ship stablecoin-adjacent fintech infrastructure into African micro-commerce every week. We have the *user side* (Coach + Pulse) that surfaces disputes, and the *settlement side* (Witness + Mesh Escrow) that resolves them. The whole loop lives in production repos. Circle's grant funds putting the missing Arc + USDC + CCTP mainnet layer under it, not funding us to discover the product.

## Ask

- Milestone-based USDC funding across the 3 milestones above (indicative 25,000 USDC).
- Circle technical mentorship on CCTP V2 + StableFX integration correctness (a review pass would save us 2 weeks of specs-reading).
- A slot in Circle's co-marketing pipeline — a blog post at M2 + a demo at Convergence (or equivalent).

---

## Contact

- Repo: https://github.com/KaJota-inc/kajota-witness
- Live: https://kajota-witness.onrender.com
- Founder: bori7 on GitHub / @bori7 on X / Oluwabori Aduragbemi Ola on LinkedIn.
