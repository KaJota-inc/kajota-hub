# 0G Zero Cup — Round 1 submission text

Paste-ready blocks for the arena form at https://0g.ai/arena/login. Adjust labels to whatever field names the form actually uses.

---

## Project name

**Kajota Witness**

## Tagline (≤ 80 chars)

> Encrypted seller memory + AI jury for African micro-commerce — on 0G Galileo.

## One-paragraph description

Kajota Witness gives African micro-commerce sellers cross-session conversation memory that they actually own — encrypted client-side, content-addressed on 0G Storage. When an escrow dispute fires, a 3-LLM jury (prosecutor / defender / neutral) pulls those exact chats from 0G as evidence, deliberates, and writes the verdict as another encrypted blob to 0G Storage — with the verdict's root hash, ruling, and confidence committed publicly via the WitnessAnchor contract on 0G Chain. The on-chain `verdictRoot` is byte-identical to the storage CID, so anyone can cross-reference one against the other without trusting the server.

## Long description

### Problem

African micro-commerce sellers chat with buyers across WhatsApp, Instagram DMs, and platform inboxes. None of those records are portable, none are seller-owned, and when escrow fires there's no neutral way to decide who's right. Platforms either side with whoever shouts loudest, or refer to centralized "trust & safety" pipelines that the seller has no visibility into.

### What Witness does

1. **Memory.** Every conversation Coach handles is AES-256-GCM encrypted client-side, uploaded as a content-addressed blob to 0G Storage, and indexed locally for retrieval-as-evidence. The encryption key never leaves the seller's environment.

2. **Court.** When a dispute is filed, Witness embeds the buyer's claim, retrieves the top-K relevant past chats from the index, downloads + decrypts them from 0G, and hands them to three LLM jurors in parallel: a prosecutor (argues for the buyer), a defender (argues for the seller), and a neutral analyst. A judge model synthesizes a ruling: `refund_buyer | release_to_seller | split_50_50 | escalate_to_human`.

3. **Anchor.** The verdict is encrypted, uploaded to 0G Storage as its own blob, AND committed on 0G Chain via the deployed `WitnessAnchor` contract — disputeId pseudonym, verdict root hash, ruling, and confidence basis points. The on-chain root matches the storage CID byte-for-byte.

### Why 0G

The Zero Cup rules require that 0G do real work — *"if it runs the same without it, that's a bolt-on and it doesn't qualify."* Witness has no fallback storage layer. Three independent 0G surfaces are each load-bearing:

- **0G Storage** — every chat blob and every verdict blob. Remove it, the app has no memory.
- **0G Chain (storage txs)** — settles every upload, issues every CID. Remove it, no provenance.
- **0G Chain (WitnessAnchor contract)** — public commitment of each verdict. Remove it, every ruling becomes "trust me."

### Trustless verification

The deployed `/verify/:cid` route runs **four independent cross-checks** on any 0G CID:

1. **0G Storage existence** — attempt to download the blob from Galileo nodes
2. **Local index match** — show what this Witness instance recorded about the CID
3. **0G Chain anchor** (for verdicts) — call `WitnessAnchor.getVerdict(disputeId)` and surface a `matchesStorageCid` boolean that's true iff the on-chain `verdictRoot` is byte-identical to the storage CID
4. **Decryption** — using the local key, reveal the original content

A third party running their own Witness server can rely on checks 1 + 3 alone — those are sufficient to prove "the verdict that was published is byte-identical to the blob anyone can fetch from 0G." Without our chain anchor + storage stack, that proof has no substrate.

## Tracks / categories

Pick whichever the arena form offers that fits. Most likely matches:

- AI agents
- DeFi / commerce / payments
- Storage / data
- Tooling / infra

## Built during the tournament window

✅ **Yes — start to finish.** New repo created Fri Jun 19, 2026 evening. First commit pushed Sat Jun 20, 2026 evening (initial commit hash `4d68253`). No pre-existing product, no fork. Commit history starts at tournament-window initialization and runs continuously.

## Public repo URL

https://github.com/KaJota-inc/kajota-witness

## Live build / demo

- **Live URL:** **https://kajota-hub.onrender.com/witness**
  - [`/ui`](https://kajota-hub.onrender.com/witness/ui) — file disputes, watch the jury, see verdicts land on chain
  - [`/verify`](https://kajota-hub.onrender.com/witness/verify) — paste any of the sample CIDs below and see the 4-way cross-check
- **Demo video (3 min):** [YOUR LOOM/YOUTUBE URL HERE — record per `docs/DEMO.md`]
- **Local run instructions:** see `README.md` Quick Start section

> ⏱ **Cold-start note:** Render free tier sleeps after 15min idle. First hit after a quiet stretch adds ~30s wake + ~30s embed-model rehydrate. An UptimeRobot ping on `/health` every 14 min keeps it warm for the judging window.

## On-chain artifacts (verifiable now)

All produced by the **deployed Render instance** — judges can paste these into [the live `/verify` page](https://kajota-hub.onrender.com/witness/verify) and watch all 4 cross-checks pass.

| Artifact | Link |
|---|---|
| WitnessAnchor contract | https://chainscan-galileo.0g.ai/address/0x2f1D3a881cfbeA01Cf55f3cAd125aA32Bf8cEC94 |
| Contract deploy tx | https://chainscan-galileo.0g.ai/tx/0x2a5b4224ae342279c3c22384402195d3109a4d3ee9afa24a27c45a0e4d2ea784 |
| Sample chat blob (sandals-haggling) | https://storagescan-galileo.0g.ai/tx/0x9d84ed8ca92a1c7b67f94d51a0b164ce29293bb35e0bd684fc34b5d589f19c0f |
| Sample chat blob (return-policy) | https://storagescan-galileo.0g.ai/tx/0xbe8ef53ff4c76c78a4c0dafc018dba35ba2567ea52bdad8d01dd35446017e179 |
| Sample chat blob (delivery-eta) | https://storagescan-galileo.0g.ai/tx/0xacdb7775f330339eb0c3533de297c4411145583b210db2aea442e0791d25c7a2 |
| Sample verdict blob (release_to_seller) | https://storagescan-galileo.0g.ai/tx/0xa9183d1ac0e9558fbac8501ce6034383122d36b4955259cf14d02448c092e5fb |
| Sample verdict on-chain anchor tx | https://chainscan-galileo.0g.ai/tx/0x7e58a83d7497caf7b83877fa818e86a2502903c9c7367a9c9dbd0db888942358 |

## Stack

- **Runtime:** Node 22, TypeScript
- **HTTP server:** Fastify 5
- **0G:** `@0gfoundation/0g-storage-ts-sdk` v1.2.10 (Galileo Turbo indexer)
- **Contract:** Solidity 0.8.20, compiled via `solc-js`, deployed via `ethers` ContractFactory (no Hardhat)
- **Embeddings:** `@xenova/transformers` — `Xenova/all-MiniLM-L6-v2` (384 dims, runs in-process)
- **Vector index:** JSON file + cosine top-K (replaceable; chosen for hackathon scale)
- **LLM:** Groq `llama-3.3-70b-versatile` via OpenAI-compatible API (free tier)
- **Encryption:** Node `crypto`, AES-256-GCM envelope
- **UI:** Single static HTML page — Tailwind CDN + vanilla JS fetch. No build step.

## Performance (verified)

| Stage | Time |
|---|---|
| Chat blob upload to 0G Storage | ~17s |
| Evidence query (embed + top-K download + decrypt) | ~6s |
| Jury deliberation (3 jurors parallel + judge, Groq) | ~1.5s |
| Verdict blob upload to 0G Storage | ~14s |
| Verdict on-chain anchor | ~16s |
| **End-to-end dispute (all of the above)** | **~38s** |

## Cost

$0. 0G testnet + Groq free tier.

## Submission checklist

- [x] Repo public on GitHub (`KaJota-inc/kajota-witness`)
- [x] WitnessAnchor contract deployed on 0G Galileo
- [x] Companion Coach integration branch + PR (`KaJota-inc/kajota-coach#2`)
- [x] **Live build deployed at https://kajota-hub.onrender.com/witness**
- [x] Sample CIDs on-chain + verifiable via deployed `/verify`
- [x] DEMO.md + SUBMISSION.md ready
- [ ] Recorded 3-min demo per `docs/DEMO.md`
- [ ] Uploaded video to Loom / YouTube (unlisted is fine)
- [ ] Replaced `[YOUR LOOM/YOUTUBE URL HERE]` above with real URL
- [ ] Filled the arena form using these blocks
- [ ] Submitted before Mon Jun 22, 2026 18:00 UTC (Round 1 deadline buffer)

## Known limitations (transparency for judges)

- **Retrieval quality on tiny corpora.** MiniLM-L6-v2 (384 dims) sometimes misranks when chats share lexical surface area (e.g., "shipping" vs "delivered"). Top-K=3 mitigates for jury use; a BM25+embedding hybrid is the proper fix and is out of scope for Round 1.
- **No Mesh escrow integration yet.** The current `WitnessAnchor` contract records verdicts but does not release escrowed funds. Wiring to KaJota's existing Mesh escrow on Mantle Sepolia is the natural next step but out of scope for this round.
- **JSON-file index.** SQLite or LibSQL is the obvious upgrade; not needed at hackathon scale.

## Coach integration — already shipped

The companion patch in `KaJota-inc/kajota-coach` is live on branch [`feat/witness-memory-integration`](https://github.com/KaJota-inc/kajota-coach/tree/feat/witness-memory-integration) (commit `1d7c570`).

After every Coach conversation turn, the agent's FastAPI server fires a fire-and-forget POST to Witness `/memory` mirroring the (user message, agent response) pair as an encrypted blob on 0G Storage. The integration is:

- **Non-blocking** — `asyncio.create_task()` runs the POST in the background. Coach's chat response never waits on the ~17s 0G upload.
- **Soft-fail** — if Witness is down, Coach logs one line and moves on. Witness availability never breaks Coach.
- **Opt-in** — disabled unless `WITNESS_URL` env var is set. Coach behaves byte-identically to before the patch when off.
- **End-to-end verified** — `agent/scripts/witness_smoke.py` posts a fake turn through the real `witness_client.py` and confirms a CID lands.
- **Minimal splice** — one new isolated module + one import + one one-line call in `_run_agent_turn()`.

Translation: Mesh disputes can now pull real Coach conversations from 0G as evidence. Not a roadmap promise — running today.

## What we'd build next

1. **Mesh escrow integration** — when WitnessAnchor records a verdict, automatically call `releaseToSeller()` or `refundToBuyer()` on the existing Mesh escrow contracts on Mantle Sepolia. Closes the loop from chat → dispute → ruling → fund movement.
2. **Hybrid retrieval** — BM25 + embedding cosine, weighted blend. Fixes the lexical-overlap miss documented in README.
3. **Multi-seller scaling** — per-seller key derivation (HKDF on a Privy-managed root key), per-seller index sharding, optional 0G KV for the index itself (eat our own dogfood).
4. **Deploy Coach with WITNESS_URL set** — the Render-deployed instance currently runs without the mirror. Flipping a single env var in Render makes every production seller turn flow into Witness.
