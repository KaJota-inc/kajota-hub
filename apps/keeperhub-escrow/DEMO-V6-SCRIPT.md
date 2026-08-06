# Demo v6 — voice script

**~95 seconds · ~230 words · conversational pace (~145 wpm)**

Records as seven independent takes. Every claim below was verified live on
2026-08-06 — see "Honesty notes" at the end for the two lines deliberately
kept narrow.

**Why re-cut at all:** v5 ([youtu.be/7ltsrdlQGNI](https://youtu.be/7ltsrdlQGNI))
predates the auditor, the refusal gate, the autonomous watcher, and the merged
PR. It shows a weaker product than the one that exists, and it's the artefact
judges actually watch.

**Tone:** calm, matter-of-fact. The content is confident so the delivery
doesn't need to be. Resist product-launch voice — this lands harder flat.

---

## 1 · HOOK (0:00–0:12)

**Screen:** the console mid-deposit — red ✗ line and `Verdict: HOLD`. Hold the frame.

> Most escrow demos show you money moving.
>
> This one starts with an agent refusing to move it.
>
> A buyer just paid. And Coach said no.

*Beat after "said no." Let HOLD sit on screen a second.*

---

## 2 · WHAT IT IS (0:12–0:26)

**Screen:** scroll up to the hero — "Coach decides. KeeperHub ships."

> Kajota Coach is a CFO for onchain escrow.
>
> It decides which payments are safe to release, and KeeperHub signs the
> transaction. Coach never touches a private key.
>
> But the interesting part isn't when it says yes.

---

## 3 · THE REFUSAL, IN FULL (0:26–0:46)

**Screen:** zoom the log — six rules, ticks and the one ✗. Click **Confirm receipt
as buyer**. Rules re-run green, `Verdict: RELEASE`, then the KH execution and the
Sepolia tx link.

> Money moved into escrow — and nothing else happened yet. The buyer hasn't
> confirmed anything.
>
> So Coach holds it, and tells you exactly which rule failed.
>
> Now the buyer confirms. Same six rules, one signal different.
>
> Release. KeeperHub signs it. Fifteen seconds, on Sepolia.

*Slight emphasis on "one signal different" — that's the whole idea in four words.*

---

## 4 · WHERE THE MODEL IS (0:46–1:02)

**Screen:** the "Where the agent actually is" section, then the triage endpoint
returning `isDispute: true`, `category: partial`.

> People ask where the AI is. Here's the honest answer.
>
> The release decision is deterministic. Six rules, same inputs, same verdict,
> every time. Money shouldn't move on a sampled token.
>
> The model does the job it's actually better at — reading what a buyer wrote
> and deciding if it's a real complaint. No keyword list reads English.
>
> And it can only ever block a release. It can never cause one.

*Last line is the most important sentence in the video. Slow down slightly.*

---

## 5 · THE PR AND THE AUDITOR (1:02–1:20)

**Screen:** merged PR #1857 on GitHub — show the purple MERGED badge. Cut to the
audit page, click **Send request**, show the report card with red issues and green fixes.

> While building this, we hit three field-name traps in KeeperHub's own docs.
> One of them silently ignores the field you set and signs with a different
> wallet.
>
> We filed the fix. KeeperHub merged it.
>
> Then we built the tool that enforces it — so Coach audits its own workflow
> before it ever fires.

---

## 6 · IT DOES THIS ALONE (1:20–1:33)

**Screen:** `/keeperhub/autonomous` — tick counter and decision log.

> None of this needs a browser open.
>
> There's a loop on the server reading Sepolia, running the same rules on a
> timer.
>
> It released that one on its own. Nobody clicked anything.

---

## 7 · CLOSE (1:33–1:40)

**Screen:** back to the console hero, then the URL card.

> Coach decides. KeeperHub ships.
>
> And every decision is one you can read, rule by rule, before the money moves.

---

# Production notes

**Recording**
- One file per section: `v6-1.m4a` … `v6-7.m4a`.
- Leave ~1s of silence at each end — gives whisper clean word boundaries and
  room to breathe the cuts.
- Flubbed line: pause two seconds, say it again. Last clean read wins; no need
  to restart the section.

**Screen capture**
1. The deposit → HOLD → confirm → autonomous release flow — **needs your wallet**.
   Hard-refresh first (⌘⇧R); several fixes landed after the last capture.
   Record the ~20 seconds of dead air before the watcher fires. That silence
   *is* section 6.
2. Everything else I can capture headlessly.

**Post**
- whisper.cpp word-level timing (same pipeline as v5)
- Cut screen capture to the VO, not the reverse
- Word-level subtitles burned in via PIL → ffmpeg overlay
- Target ≤1:45 final

**Prior VO takes** (kept — useful for tone matching, not reusable verbatim
since the script changed): `~/Downloads/vo-take.m4a` (90.7s),
`~/Downloads/vo-wallet.m4a` (21.5s).

---

# Honesty notes

**Section 6 says "It released that one on its own."** True as of 2026-08-05 —
`KH_WATCHER_LIVE=1` is armed and a real unattended release landed:
[0x7d42968f…4d1c215a](https://sepolia.etherscan.io/tx/0x7d42968fffeed4bceeb224c438aeed518aa38bf1c08b3856a9dc82d64d1c215a),
block 11427228, execution `ia88nu1eqwv3zhtg929oo`. The watcher held first, the
buyer confirmed, and it fired on its next tick with nobody at the keyboard.

⚠️ **If `KH_WATCHER_LIVE` is ever unset, this line stops being true** — the
watcher reverts to dry-run and only logs what it *would* do. Check
[`/keeperhub/autonomous`](https://kajota-hub.onrender.com/keeperhub/autonomous)
shows `"mode": "live"` before recording section 6.

**Section 5 says "KeeperHub merged it"** — true. Commit `ee4b6a0`, merged by
@suisuss on 2026-08-03 into `KeeperHub/keeperhub`. Not "adopted our proposal"
or similar inflation.

**Section 3 says "Fifteen seconds"** — the operator-triggered release measured
~11.5s end to end; "fifteen" is a safe round number, not a stretch.
