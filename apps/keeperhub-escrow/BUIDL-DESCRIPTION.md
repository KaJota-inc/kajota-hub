# DoraHacks BUIDL #47293 — description

Live at https://dorahacks.io/buidl/47293 · deadline 2026-08-13 11:00.
This file is the source of truth; the Lexical editor on DoraHacks gets a
whole-document replace from it.

## Changes in this revision

1. **New section — "The auditor catches what KeeperHub's own validator
   doesn't."** The strongest evidence in the project was nowhere in the
   submission: KH's own `validate_workflow` passes our production workflow,
   ours fails it. Verified 2026-08-11 through KeeperHub's MCP server.
2. **Corrected "+64 lines" → "+80 −12 across 3 files."** The live
   description understated the merged PR. `gh api` reports additions 80,
   deletions 12, 4 commits, 3 files changed.
3. **Video swapped** to the v6 cut — `youtu.be/cplXyWAxm0U`, 2m 11s. The old
   link `7ltsrdlQGNI` predates the refusal gate, the auditor and the watcher.
4. **Autonomous release now cites the split and the latency**, both readable
   on a block explorer rather than asserted by our own page.
5. **KeeperHub MCP server added** to surfaces used — it is how the auditor
   comparison was run.

⚠️ The video URL also appears in the BUIDL's **links** field, which is edited
separately from the description body. Both need changing.

---

I spent years building payments infrastructure in Nigeria, and the failure that never leaves you is settlement that stalls — money sitting in escrow for days because no human has clicked "release". Not a technical failure. Nobody got to it.

Coach is the agent I wanted then. It decides which escrows to release, when, and why — deterministic rules decide, the model only explains — and before it fires anything it audits its own KeeperHub workflow against the trap catalogue I shipped into KeeperHub's own docs (PR #1857, merged). Coach shipped the docs. Then Coach shipped the tool that enforces them.

Every claim below is clickable: a merged PR in KeeperHub's repo, a fully unattended release on Sepolia where the only human actions were the buyer's own deposit and confirmation, and a live page you can paste any workflow into and watch it get audited.

**Bounty (Onboarding UX Improvement):** PR KeeperHub/keeperhub#1857 — MERGED into KeeperHub on 2026-08-03 as commit ee4b6a0 (reviewed by @joelorzet, iterated once, merged by @suisuss). +80 −12 across 3 files, now shipping in KeeperHub's canonical docs, covering three field-name traps direct-API builders hit: `web3Connection` vs the silently-ignored `integrationId`, `functionArgs` as a JSON-encoded string, and the HTTP-trigger template syntax `{{@trigger-1:HTTP.x}}`.

## The auditor catches what KeeperHub's own validator doesn't

This is the part we'd point a judge at first, and it implicates our own code.

Our production release workflow — `1pyjp0c15z2h558jld8pn`, the one that signs every release in this submission — configures its signer with `integrationId`. That is the exact field PR #1857 documents as accepted-then-ignored. Run that workflow through both validators:

- **KeeperHub's own `validate_workflow`** (through KH's MCP server) → `{ "valid": true, "nodeCount": 2 }`
- **Coach's auditor** → `FAILED`, `SILENTLY-IGNORED-INTEGRATION-ID`, with the one-line fix

It has never mis-fired for us, and the reason is luck rather than configuration: `list_integrations` returns exactly one web3 integration for our organisation, so the ignored field's fallback happens to land on the intended keeper. Add a second wallet and nothing in the workflow determines which one signs.

We are deliberately not claiming more than that. We cannot demonstrate a mis-signed transaction, because there is no second wallet to mis-route to. The failure is latent — which is exactly what makes it a job for a linter rather than a test.

That is the argument for the auditor in one screenshot: the traps we documented upstream are still not machine-checkable by the platform, so Coach checks them itself before it fires.

## What we shipped

Coach is the merchant's autonomous CFO for onchain escrow. It decides which deposits may be released, refuses the ones that shouldn't be, audits its own KeeperHub workflow against the traps we documented upstream, and KeeperHub's Turnkey wallet signs the release under EIP-7702. USDC splits 85 / 15 to wholesaler and coseller in one keeper-signed tx.

The invariant that runs through all of it: **deterministic decides, LLM explains.** Money never moves on a sampled token.

## Proof it runs unattended

A server-side loop polls Sepolia, evaluates the same rules on a timer, and fires KeeperHub itself. Captured end to end — no browser involved past the buyer's own two actions:

```
[info] autonomous watcher started · tick 20s · LIVE
[info] now watching this deposit
[dim ] HOLD — Buyer has not confirmed and only 0.0 of 7 days elapsed
[info] buyer confirmed receipt — will release on the next tick
[ok  ] RELEASE — Buyer explicitly confirmed receipt. Seller has 8
       successful releases and 0 disputes (100% success rate).
[ok  ] fired KeeperHub workflow autonomously · executionId=ia88nu1eqwv3zhtg929oo
```

Autonomous release tx **0x7d42968f…4d1c215a** — block 11427228, 114,808 gas, `sponsored: true`, signed by KeeperHub's keeper while nobody was watching. On the explorer you can read the two things our own page can only assert: the split executing as **0.085 USDC to the seller and 0.015 as fee**, and **"confirmed within ≤ 12.364 secs"** against our ~15s latency claim.

Deposit `0x3aac4e80…ce635764` · KH execution `ia88nu1eqwv3zhtg929oo` · 11,491 ms
Live loop state + rolling decision log: `/keeperhub/autonomous`

It held first and said why. The buyer confirmed. It changed its mind on its own timer, for a stated reason, and submitted a real transaction. The only human actions in that sequence belong to the buyer — nobody touches a release button. Ships **dry-run by default**; `KH_WATCHER_LIVE=1` arms it, because unattended transaction submission should be a decision an operator makes explicitly.

## Try it in 30 seconds

- **Watch Coach refuse, then release** — kajota-hub.onrender.com/keeperhub — deposit 0.10 test USDC and Coach holds it, printing the rule that failed. Confirm receipt and the watcher takes it from there. No wallet? The same page runs all three verdicts against the live endpoint, and replays a real release against the escrow's idempotency guard.
- **Audit any workflow** — `/concierge/coach/audit-workflow` — a real page with a try-it form. Paste a workflow, get a report card with a copy-pasteable fix per issue.

## Where the agent actually is — and where it deliberately isn't

Most "AI agent" submissions put a model in the decision path. We deliberately did not: a release layer that always says yes isn't a decision layer, and a non-deterministic one is worse. The split:

- **Deterministic** — escrow state, acceptance window, dispute flag, amount cap, seller reputation. Six rules, pure functions, same inputs → same verdict every time.
- **LLM** — two jobs it is genuinely better at: writing the plain-English explanation, and reading a free-text buyer complaint to decide whether it is a real dispute. No keyword table reads English properly.
- **The agent** — picks which question to ask and fills the inputs from prose. Ask `/concierge/chat` "someone paid two weeks ago and has gone quiet — should I release?" and the trace shows `CALL should_release` with `days_since_deposit: 12` extracted from the sentence.

The safety boundary is **structural, not a promise**. Dispute triage emits a classification that a rule consumes — so the model can cause a HOLD or a REJECT, and can never cause a RELEASE. `activeDispute=false` merely declines to block; every other hard rule still has to pass on its own. The worst a bad classification can do is stall a payout for a human to read.

## Live artefacts

- Merged docs PR: KeeperHub/keeperhub#1857 · commit ee4b6a0
- Console — hold → confirm → autonomous release, auditor, CFO, watcher: kajota-hub.onrender.com/keeperhub
- Autonomous release tx: 0x7d42968f…4d1c215a
- Operator-triggered release tx: 0xc0acf8ed…354b0
- KeeperHub workflow: app.keeperhub.com/workflows/1pyjp0c15z2h558jld8pn
- Demo video (2m 11s): youtu.be/cplXyWAxm0U
- Full DX teardown: SUBMISSION-KEEPERHUB.md
- Repos: kajota-mesh · kajota-coach · kajota-hub

## Agent-callable API

Every endpoint is content-negotiated — a browser gets documentation, an API client gets JSON, POST does the work. None of them return 405 when clicked.

- `POST /concierge/coach/should-release` → release | hold | reject, plus every rule evaluated
- `POST /concierge/coach/triage` → dispute classification from free text
- `POST /concierge/coach/audit-workflow` → workflow report card
- `POST /concierge/chat` → agent turn with all three as tools
- `GET /keeperhub/autonomous` → watcher state and rolling decision log

## KeeperHub surfaces used

- HTTP trigger workflow
- `web3/write-contract` action
- Turnkey wallet integration — EIP-7702 keeper delegation
- REST `POST /api/workflows/{id}/execute` — from Coach, and from the watch loop
- REST `GET /api/workflows/{id}` — the auditor reads workflows through KH's own surface
- **KeeperHub MCP server** — `validate_workflow`, `get_workflow`, `list_integrations`, `get_execution`. How the auditor comparison above was run, and how we confirmed the autonomous execution was sponsored and verified.
- Live executions dashboard / audit trail

## Reproduce

```
git clone https://github.com/KaJota-inc/kajota-mesh
cd kajota-mesh && git checkout hackathon/keeperhub
pnpm install
export DEPLOYER_PRIVATE_KEY=… KEEPERHUB_API_KEY=kh_…
pnpm --filter @kajota-mesh/contracts keeperhub-demo:sepolia
```

34 tests across the two rules engines — 15 CFO, 19 auditor.

The demo video is rebuilt from the live site by a committed pipeline, not hand-edited footage: every frame is captured from the deployed console at build time, so the video cannot drift from what the site does.

## The story

We hit three real doc gaps while wiring the release path, filed a targeted PR, iterated with the maintainer, and got it merged into KeeperHub's canonical docs. Then we turned the same discovery into an audit tool Coach runs before it fires anything — and pointed it at our own production workflow, where it found a trap KeeperHub's own validator passes.

Coach never sees a private key, never eats gas volatility, never handles retries. KeeperHub is the last mile between an agent's decision and confirmed on-chain state — and the decision is one you can read, rule by rule, before the money moves.
