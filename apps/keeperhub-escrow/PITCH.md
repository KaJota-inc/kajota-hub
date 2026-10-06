# Finalist pitch — Kajota × KeeperHub

**Aug 17–19, 2026 · live to the KeeperHub judging panel · BUIDL #47293**

> Final rankings and winners are decided from those live pitches alongside
> the scored review. — the hackathon's own rules

⚠️ **Confirm your slot length before rehearsing.** The rules say "a short
pitch session" and nothing more. This is built as **5 minutes**, with a
**3-minute** compression marked `[CUT]` for a shorter slot. Ask in
`#general` when the invite arrives.

---

## Who is actually in the room

Not strangers. `@joelorzet` reviewed PR #1857 and requested changes;
`@suisuss` merged it. `Luca | KeeperHub` runs the announcements and the
office hours.

Three consequences, and they shape everything below:

1. **Do not explain KeeperHub to KeeperHub.** No slide on what the
   execution layer is or why the last mile is hard. They wrote it. Every
   second spent there is a second not spent on what you found.
2. **They already know your work.** Someone in that room read your diff
   line by line and asked for changes. You are the contributor with the
   merged docs PR, before you say a word.
3. **The strongest thing you have is a finding about their product.**
   Delivered as a gift, not a gotcha.

## What the rubric rewards, in its own words

"Execution is weighted heavily, because that is the point." Then: use of
KeeperHub surfaces, reliability and observability, originality, integration
quality.

Lead with the transaction. Everything else is support.

---

# The 5-minute pitch

## 0:00–0:30 — Open on the refusal

> Most agent demos show you money moving. I want to start with mine
> refusing to move it.
>
> *[HOLD on screen — red ✗, `Verdict: HOLD`]*
>
> A buyer paid. The money is in escrow. And Coach said no — because the
> buyer hasn't confirmed receipt, and it will tell you exactly which rule
> stopped it.

*Beat. Let HOLD sit. Do not narrate over it.*

## 0:30–1:00 — Why I built it

> I spent years on payments infrastructure in Nigeria. The failure that
> stays with you isn't fraud or downtime — it's settlement that stalls.
> Money sitting in escrow for days because no human got round to clicking
> release. Not a technical failure. Nobody got to it.
>
> That's what this agent is for.

*First person. This is the only part of the pitch nobody else can give.*

## 1:00–2:00 — The thing itself `[CUT: compress to 30s]`

*Click **Confirm receipt**. Rules re-run green. Release fires.*

> Same six rules. One signal different. Release — and KeeperHub signs it.
>
> The division is the whole design: **the rules decide, the model
> explains.** Six deterministic rules, pure functions, same inputs, same
> verdict every time. Money never moves on a sampled token.
>
> The model does the two jobs it's actually better at — writing the
> explanation, and reading a free-text buyer complaint to decide whether
> it's a real dispute. No keyword table reads English.
>
> And the boundary is structural, not a promise: triage emits a
> classification that a *rule* consumes. So the model can cause a HOLD or
> a REJECT. It can never cause a RELEASE.

## 2:00–3:15 — The finding *(the centrepiece)*

> While wiring this I hit three field-name traps in your docs. I filed the
> fix, Joel reviewed it, and it merged on August 3rd.
>
> But here's the part I want to show you.
>
> *[Split screen: KH `validate_workflow` → `{"valid": true}` · Coach's
> auditor → `FAILED · SILENTLY-IGNORED-INTEGRATION-ID`]*
>
> This is my own production workflow — the one that signs every release in
> this submission. It configures its signer with `integrationId`, which is
> the field my own PR documents as accepted-and-ignored.
>
> **Your validator passes it. Mine fails it.**
>
> It has never mis-fired for me, and the reason is luck, not config: my org
> has exactly one web3 integration, so the fallback lands on the right
> wallet by accident. Add a second wallet and nothing in that workflow
> decides which one signs.
>
> I can't show you a mis-signed transaction, because I have no second
> wallet to mis-route to. The failure is latent — which is exactly what
> makes it a job for a linter and not a test.
>
> That's the argument for the auditor in one screen: the traps I
> documented upstream still aren't machine-checkable by the platform. So
> Coach checks them itself, before it fires.

*This is the moment. Slow down. Do not rush the "your validator passes it"
line, and do not apologise for it.*

## 3:15–4:15 — Proof it runs unattended `[CUT: compress to 40s]`

> None of this needs a browser open. There's a loop on the server reading
> Sepolia, running the same rules on a timer.
>
> *[block explorer]*
>
> It released this one on its own. Nobody clicked anything. Block
> 11427228 — and two things there I can't assert from my own page: the
> 85/15 split executing as 0.085 USDC to the seller and 0.015 as fee, and
> confirmation inside 12.4 seconds against my ~15-second claim.
>
> Gas was sponsored — your relayer paid it, not my merchant.
>
> It ships **dry-run by default**. `KH_WATCHER_LIVE=1` arms it, because
> unattended transaction submission should be a decision an operator makes
> on purpose.

## 4:15–4:45 — Surfaces, briefly

> Workflow builder, web3 write-contract, Turnkey under EIP-7702, the REST
> API, the audit trail, your MCP server — that's how I ran the validator
> comparison — and as of this week x402: the release endpoint is
> paywalled, 0.01 USDC on Base Sepolia, settled before the keeper is ever
> called. Payment first, execution second. A failed settlement never
> reaches your workflow.

## 4:45–5:00 — Close

> Coach never sees a private key, never eats gas volatility, never handles
> retries. KeeperHub is the last mile.
>
> And every decision is one you can read, rule by rule, before the money
> moves.

---

# Demo run-sheet

**Run `preflight.sh` within the hour before your slot.** It fails if any
claim above has stopped being true.

| # | screen | action | fallback if it hangs |
|---|---|---|---|
| 1 | console, CFO panel | already on **Not shipped yet** → HOLD | screenshot `frames/s1-hold.png` |
| 2 | same | click **Happy path** → RELEASE | `frames/s3-release.png` |
| 3 | terminal / split | `validate_workflow` vs auditor | pre-captured JSON, both sides |
| 4 | block explorer | the autonomous tx | `frames/s6-explorer.png` |
| 5 | 402 challenge | `curl` the x402 endpoint | `frames/` + printed JSON |

**Warm the service 10 minutes before.** Render idles; a cold first request
costs ~30s and it will happen live on screen.

**Have `kajota-coach-demo-v6.mp4` open in a tab.** If the network dies,
play 0:00–0:51 and narrate over it. Never debug live — cut to the video,
keep talking.

---

# Q&A bank

Answer briefly, then stop. Do not fill silence.

**"Isn't this just a cron job with extra steps?"**
> The schedule is the easy half. The hard half is the decision and the
> refusal — six rules, and a stated reason for every hold. A cron job
> releases on time. This one declines to, and tells you which rule said no.

**"Where's the agent? This looks deterministic."**
> Deliberately. A release layer that always says yes isn't a decision
> layer, and a non-deterministic one is worse. The agent picks which
> question to ask and fills the inputs from prose; the model reads
> free-text disputes. It can block a release; it can't cause one. That's
> enforced by the call graph, not by a prompt.

**"You said your own workflow is misconfigured. Why should we trust it?"**
> Because I found it and told you, rather than shipping past it. The
> release path is correct in effect today — one wallet, so the fallback
> lands right. The auditor is what stops it being luck. I'd rather show
> you a real latent bug in my own code than a clean demo.

**"Did the x402 payment actually settle?"**
> *If yes:* here's the settlement tx and the x402scan entry.
> *If not yet:* the endpoint is live and quoting — GET it and you'll see
> the challenge. The paid call is signed by a wallet I control; I'll send
> the tx the moment it's run. Don't claim more than has happened.

**"What breaks at scale?"**
> Three things I know about. The watcher's state is in-memory, so it
> re-derives from chain on restart rather than resuming. The rules read a
> single escrow per tick — that's a batch call at volume. And a
> per-release x402 charge needs an aggregated scheme, not `exact`, once
> you're past demo volumes.

**"What would you build next?"**
> Multi-wallet routing, which is what the `integrationId` finding is
> really about — and pushing the auditor upstream as a lint rule in your
> CLI, so nobody hits those traps at all.

**"How long did this take?"**
> Roughly two and a half weeks, solo.

---

# Rules for the room

1. **Do not explain KeeperHub.** They built it.
2. **The refusal is the hook.** Never open on a success.
3. **Say "your validator passes it" without hedging.** They are engineers.
   A precise, well-scoped finding reads as respect, not attack.
4. **Name the limits before they ask** — one wallet, latent not observed,
   in-memory watcher state. Volunteering a limit buys more credibility
   than any claim you make.
5. **Never debug live.** Cut to the video, keep talking, move on.
6. **Stop when you're done.** Do not fill the silence at the end.

## Do not say

- "Revolutionary", "game-changing", "the future of".
- "AI agent" as the headline — the deterministic core is the interesting
  part, and this room knows it.
- Anything you haven't verified that week. Run `preflight.sh` first.
