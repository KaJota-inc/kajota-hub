# H0 post-mortem → KeeperHub actions (before Aug 13 deadline)

Kajota Pulse lost H0 (Monetizable-B2B) to entries that out-*framed* it, not out-built it (see `[[hackathon-winning-playbook]]` H0 addendum). KeeperHub already has **4 of the 6 winning traits** — this doc closes the 2 gaps. Do NOT add features this close to the deadline; the ROI is positioning + a fresh video.

## Already nailed (leave alone)
1. **Surprising use of the sponsor primitive** — Coach audits its *own* KeeperHub workflow against a trap-catalogue it **merged into KH's own docs** (PR #1857). Stronger than any H0 winner's DB trick.
2. **Constraint-as-feature** — "deterministic decides, LLM explains"; the model can HOLD/REJECT but never RELEASE.
4. **Judge-verifiable evidence** — autonomous Sepolia tx + merged PR + live no-login console.
5. **Depth** — 34 CFO/auditor tests + autonomy proof.

## GAP 1 (highest ROI) — re-cut the demo video (~90s DX clip)
v5 (`youtu.be/7ltsrdlQGNI`) was cut BEFORE the CFO+auditor+"MERGED" rework — judges watch it and see none of the differentiators. Re-cut, DX-first (also the Onboarding-UX bounty pitch). VO takes saved: `~/Downloads/vo-take.m4a`, `~/Downloads/vo-wallet.m4a`.

| Time | Show | Say (first-person) |
|---|---|---|
| 0:00–0:12 | /keeperhub console | "In Nigerian payments, settlement stalls for days waiting on a human to click *release*. I built the agent that clicks it — safely." |
| 0:12–0:38 | **Paste a workflow JSON → live audit report card**; point at "Trap 01: `integrationId` silently ignored"; flash the merged PR | "Paste any KeeperHub workflow and Coach audits it. These rules *are* the docs I merged into KeeperHub — PR #1857." |
| 0:38–0:58 | `should-release` verdict + rule names + narration | "Deterministic rules decide; the LLM only explains. It can hold or reject — it can never release." |
| 0:58–1:22 | Watcher log (HOLD → buyer confirms → RELEASE → fired KH workflow) → cut to the Sepolia tx on Etherscan | "Fully unattended. The only human actions are the buyer's own deposit and confirmation — no operator touches the release." |
| 1:22–1:30 | The evidence row (Gap 3) | "Merged PR, live console, on-chain proof — all one click. Built on KeeperHub." |

## GAP 2 — first-person lived-stake description opener (paste into DoraHacks)
Replace the third-person "Coach is the merchant's autonomous CFO." opener with:

> I spent years in Nigerian payments infrastructure, and the pattern that never leaves you is **settlement that stalls** — money sitting in escrow for days because no human has clicked "release."
>
> **KeeperHub Coach is the agent I wanted then.** It's a merchant's autonomous CFO: it decides which escrows to release, when, and why — *deterministic rules decide, the LLM only explains* — and before it fires a single release it **audits its own KeeperHub workflow** against the trap catalogue I shipped into KeeperHub's own docs (PR #1857, merged). Coach shipped the docs. Then Coach shipped the tool that enforces them.
>
> Every claim here is clickable: a merged PR, a fully unattended release on Sepolia where the only human actions are the buyer's own deposit and confirmation, and a live console you can paste any workflow into and watch it get audited.

## GAP 3 — one-screen "Verify everything (no login)" evidence strip
Add a row at the top of `/keeperhub` (above section 01), 4 clickable chips + a live readout:
- **Merged PR #1857** → github.com/KeeperHub/keeperhub/pull/1857
- **Autonomous release tx** → sepolia.etherscan.io/tx/0x7d42968f…4d1c215a
- **34 tests passing** (CFO 15 + auditor 19)
- **Paste-and-audit ↓** (anchor to section 04)
- tiny live status: last watcher tick + last release (from `/status`)

Mirrors H0-winner FarmOps' public `/admin/evidence` — a page a tired judge clicks, not a CLI they clone.

## Primitive-verbatim checklist (name in the first paragraph)
KeeperHub **workflow** · KH **REST execute** · **MCP/CLI** · **workflow-audit** surface · Turnkey **EIP-7702** keeper · (x402/MPP if referenced). Tells judges which corner of KH you touched.

## Judging-weight reminder (don't over-index)
KeeperHub weights: onchain-execution → KH-surface use → reliability/observability → **real-world usefulness** → integration/DX. No "Monetizable" axis — skip the pricing-model push; spend that energy on usefulness clarity.
