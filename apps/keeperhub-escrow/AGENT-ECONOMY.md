# KeeperHub — The Agent Economy Hackathon · plan

**Canonical brief:** https://dorahacks.io/hackathon/agent-economy/detail
**Verified 2026-09-10.** Second KeeperHub hackathon; we did not place in the first.

## Hard facts

| | |
|---|---|
| Submissions close | **Sep 18, 12:00 CEST — 11:00 WAT / 10:00 UTC.** "Nothing is accepted after this." |
| Time left | **~8 days** from today (Sep 10) |
| Prize pool | $5,000, stablecoins |
| Main track | **Best Integration into a Live Project** — $4,000 ranked: 1st $2,000 · 2nd $1,200 · 3rd $800 |
| Bounty | **Best KeeperHub Feature** — $1,000, two winners at $500. A merged-able PR to the KH repo. |
| Stacking | Bounty stacks with main track. **A BUIDL enters only ONE track — the bounty needs a SEPARATE BUIDL.** |
| Field so far | 177 registered (vs 471 last time). BUIDL list currently empty — everyone submits late. |
| Judging | Sep 18–25, reviewed **at repository level**. Up to 10 finalists pitch live in two parallel rooms. Winners Sep 24/25. |
| Our status | ⚠️ **NOT REGISTERED YET** — page still shows "Register as Hacker". |

⚠️ Eventbrite lists conflicting dates (Sep 6–18 6PM PDT vs Sep 7–19). The
DoraHacks page is canonical: **Sep 18, 12:00 CEST**. Do not plan off Eventbrite.

## What they're asking for, in their words

> "This time the brief is tighter. We are asking for **integrations**: agents
> and workflows that connect KeeperHub into other live projects and move value
> through them. **Live** means a project that exists and is running, with users,
> a deployed product or an active protocol behind it. We would rather see one
> working integration into a project like that than **another standalone demo**."

Named examples (explicitly "examples rather than a shortlist"): **Wayfinder,
Daydreams, Almanak**.

## Main-track rubric, in priority order

1. **Integration depth** — is there a real, *named* project on the other side, and is the integration *specific* to it?
2. **Execution through KeeperHub** — did value actually move, and can we see it?
3. **Reliability and observability** — does it survive the non-happy path?
4. **Usefulness and originality** — does it solve something real *for users of the integrated project*?
5. **Developer experience and code quality** — could another team pick this up?

Form questions worth pre-answering: which project, what the integration does,
which KH surfaces (MCP / CLI / x402 / MPP / agent-authored workflows / audit
trail), **"Testnet or mainnet?"**, and **"What still breaks or is unfinished?
A candid answer here has never hurt a submission."**

---

# How this brief maps onto why we lost last time

Every failure mode from [[project-keeperhub-hackathon]] is addressed by this
brief, which makes it unusually winnable *if* we build to the rubric rather
than to our own taste.

| last time | this brief |
|---|---|
| Our "agent refuses to execute" angle was the **median** of 190 submissions | Differentiation is now **structural** — it comes from *which live project* you pick, not from your framing |
| Everything ran on **testnet**; execution was the heaviest criterion | The form **asks outright**: testnet or mainnet |
| We invented a market ("onchain merchants with stalled escrow") | Rubric #4 is usefulness **to users of the integrated project** — the users already exist |
| `n8n-nodes-keeperhub` took top-3 on distribution leverage | Integration **is** the whole track now |
| Our bounty PR was docs for the already-stuck; brief wanted zero-to-first-tx | Bounty is now a **feature** PR judged on **mergeability** |

---

# Recommended play: two BUIDLs

## BUIDL 1 — Bounty: fix KeeperHub's own workflow validator

**Confidence: high. Start here — it is the cheapest point on the board.**

We already found, and verified through KeeperHub's own MCP server, that
`validate_workflow` returns `{"valid": true, "nodeCount": 2}` on a workflow
whose signer is configured with `integrationId` — the reserved key their
own runtime accepts and then ignores. Our auditor fails the same workflow with
`SILENTLY-IGNORED-INTEGRATION-ID`.

The bounty asks for exactly this: *"a new trigger or action, a connector, **a
developer experience improvement**. Judged on whether we can merge it and build
on it."*

Why it should win:
- The gap is **real, reproducible, and already documented in their own repo** — by us, in merged PR #1857.
- We have a working implementation with **19 passing tests** (`coach_auditor.py`) to port.
- We have merge history with the maintainers: @joelorzet reviewed #1857, @suisuss merged it.
- Mergeability is rubric #1 for the bounty, and this is a small, self-contained validator rule — not a feature they have to take a position on.

Scope: port the trap catalogue into `validate_workflow` as warnings/errors with
a fix string per issue, plus tests. Ship as a PR, then a BUIDL pointing at it.

## BUIDL 2 — Main track: KeeperHub as the execution layer for Daydreams

**Recommended, but this is the decision I need from you.**

[Daydreams](https://www.daydreams.systems/) is a named example in the brief,
it is live, open source, and its **`lucid-agents` Commerce SDK** already ships
"drop-in adapters for Hono, Express, Next.js and TanStack, giving instant
access to crypto/fiat payment rails (AP2, A2A, **x402**, ERC8004)".

The gap to fill: x402 *settles a payment*. It does not *execute an arbitrary
onchain action* with nonce management, gas estimation, MEV-private routing,
retries and an audit trail. That is exactly KeeperHub. So:

> A Lucid agent gets paid over x402 → KeeperHub executes the work that payment
> bought, deterministically, with a receipt the payer can verify.

Why this one:
- **Integration depth** — a named project the sponsor themselves suggested, and the adapter is specific to their SDK's actual interfaces, not a wrapper.
- **Feasible in 8 days** — we already built this exact shape on Aug 11: `POST /concierge/escrow/schedule-release` takes x402 payment, *then* fires a KeeperHub workflow, and returns both receipts. We point it at their SDK instead of our own escrow.
- **It is the n8n play again** — a drop-in adapter is distribution, which is the shape that won last time.
- **Mainnet is reachable** — x402 works on Base mainnet and KH sponsors gas on mainnet Ethereum. Answer "mainnet" on the form.

### Alternatives if you'd rather not

- **Aave v3 liquidation defence.** Live, huge user base, unambiguous usefulness. But **three** submissions did this last time (Sentinel, Onchain Sentinel, Ripcord) — highest collision risk in the field.
- **A live Nigerian/African onchain project** (e.g. Breet, where you already have a grant submission). Almost certainly uncontested, real users, and your domain edge is genuine. Weaker only on how legible the project is to European judges.
- **Almanak / Wayfinder.** On-brief and named, but an unfamiliar codebase to learn inside 8 days.

---

# Hard requirements — all three or it cannot be judged

- [ ] Source code link
- [ ] Short demo video **showing the integration working**
- [ ] **A link to a transaction executed through KeeperHub** — mainnet if at all possible
- [ ] Registered as a hacker (not done yet)
- [ ] Separate BUIDL for the bounty

# 8-day shape

| day | |
|---|---|
| Sep 10–11 | Register. Lock the target project. Read its SDK. Open the bounty PR early so maintainers have time to review it. |
| Sep 12–15 | Build the integration against the real project. Get value moving through KH on **mainnet**. |
| Sep 16 | Reliability pass — the non-happy path is rubric #3. Reuse `preflight.sh`. |
| Sep 17 | Demo video via the committed CDP pipeline in `demo/`. Draft the form answers. |
| Sep 18 | Submit with hours to spare, not minutes. **Re-scout the BUIDL list before finalising positioning.** |

# Rules for this one

1. **Build to the rubric, not to taste.** Last time we optimised for a narrative we liked. Integration depth is criterion #1 — the named project on the other side does more work than any framing.
2. **Mainnet.** The form asks. Testnet is a scored answer, not a neutral one.
3. **Answer "what still breaks" candidly** — they say it has never hurt a submission, and Luca's post-mortem singled out self-critical entries. It is scored honesty, so spend it well.
4. **Build something runnable in front of people.** Finalists "present the working build rather than slides, and you get asked about it."
5. **Re-scout before submitting.** The list is empty today; it will not be on Sep 18.

# Carried-over risk

- `KH_WATCHER_LIVE=1` still armed on Render from the last hackathon (21,591 ticks, `dryRun:false`). No HTTP disarm route exists — needs the env var unset and a redeploy.
- KH API key `kh_pypg1J6-…` still live and compromised (pasted in chat). Rotate before reusing it here.
