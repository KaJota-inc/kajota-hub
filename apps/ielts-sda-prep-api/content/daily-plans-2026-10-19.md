# Day 6 — Monday, 2026-10-19 — Week 1

*Source: Daily One-Look. Day 6 is route-comparison day — Imperial QRT vs
York, cost structures, funding unknowns.*

## The MELSAN read for today

- **Melancholic focus**: a *comparison table*, not prose. Two columns
  (Imperial QRT, York direct-entry), N rows (route open? funding model?
  cost? deadline? admin known-knowns? supervisor confirmed? risk level?).
  Unknowns stay marked UNKNOWN with the next action to answer them.
- **Sanguine beat**: today you record your first Speaking IELTS session.
  Recording your own voice is a Sanguine format — the beat lands when you
  hit record and the first word comes out. No perfection.
- **Risk this day touches**: R5 (QRT funding mistaken for guarantee), R6
  (York funding amount unclear), R9 (deadline / timezone mismatch).
- **Ship rule**: comparison table + explicit "unknowns to resolve this
  week" list. Even one blank row is fine as long as the next-action is
  dated.

---

## 1. PhD research / applications — 90 min

**Workbook task:** Professor-first Day 6 — Review York thesis-based
alternatives and Imperial QRT funding/deadline rules. Check whether the
projects remain open and record unanswered questions.
**Acceptance test:** route comparison with costs/funding unknowns marked,
saved to `evidence/2026-10-19/phd-route-comparison.md`.

Required rows:
1. Route open to you right now
2. Deadline (verified, with time zone)
3. Funding model (tuition + stipend terms; is funding guaranteed on
   admission or competitive-within-admitted-cohort?)
4. Required documents (CV, statement format, references, transcripts)
5. GenAI statement rule (yes/no)
6. Supervisor contact status (shortlisted/contacted/replied/confirmed)
7. Risk Register link (which R-items apply)
8. Decision: Primary / Secondary / Backup / Hold

- [ ] Route comparison table saved
- [ ] Unknowns list with dated next actions
- [ ] Risk Register updated

**Melancholic trap:** turning a comparison table into an essay. The point
is scanability on Day 48 when the submission week is live. Keep it tabular.

---

## 2. IELTS Academic — Speaking — 60 min

**Workbook task:** Record Part 1 (3 questions) + a 2-minute Part 2
response; score yourself against fluency/coherence, lexical resource,
grammar and pronunciation; note 3 improvements.
**Acceptance test:** two audio recordings + self-score + 3 improvements.

Baseline day for Speaking.

- [ ] Part 1: 3 questions, recorded (quiet room, phone recorder is fine)
- [ ] Part 2: pick a card topic, prep 1 min, speak 2 min, recorded
- [ ] Playback with the four criteria open
- [ ] Self-score 0-9 per criterion
- [ ] Three improvements named with specific action for next Speaking day
- [ ] Saved to `evidence/2026-10-19/ielts-speaking.md` with audio file paths

**Melancholic trap:** re-recording until it sounds right. The Day-1 rule
is: record once, score once. The point of the baseline is to see where
you are now.

**Sanguine beat:** your voice is the asset. Humanise the recording — a
30-sec real response is a bigger win than a 2-min scripted one.

---

## 3. System Design — 45 min

**Focus:** Timeouts and retries.
**Workbook task:** Design retry/backoff rules; explain retry storms,
idempotency and when not to retry.
**Acceptance test:** written retry policy + storm scenario + two
non-retryable error classes.

- [ ] Retry policy: max retries, exponential backoff with jitter, timeout
      per attempt vs cumulative deadline
- [ ] Retry storm scenario: all clients retry at T+1s after a transient
      failure at T; mitigation: jitter, circuit breaker
- [ ] At least two non-retryable error classes with reasoning (e.g., 401
      Unauthorized — retry won't help; 400 Bad Request — same input will
      fail again)
- [ ] Saved to `evidence/2026-10-19/sd-retries.md`

---

## 4. DSA — Java 21 — 45 min

**Focus:** Sliding window.
**Workbook task:** Solve Minimum Size Subarray Sum. Test no-solution and
one-element cases.
**Acceptance test:** O(n) sliding-window + edge cases.

- [ ] Sliding-window solution; expand `right` while sum < target, shrink
      `left` while sum >= target
- [ ] Edge: no subarray reaches target (return 0 per LeetCode spec)
- [ ] Edge: single element >= target
- [ ] Edge: whole array summing exactly to target
- [ ] Saved to `evidence/2026-10-19/dsa-min-subarray-sum.java`

---

## End-of-day row + parking lot — standard shape.
