# Day 2 — Thursday, 2026-10-15 — Week 1

*Source: Daily One-Look. Day 2 is the Imperial entry-risk pin: Bachelor's-only
candidates are not normally considered — today you write that in black and white.*

## The MELSAN read for today

- **Melancholic focus**: write the Imperial entry-risk note in writing. Not
  mentally, not later, today. The Risk Register's R1 (High / Critical) is
  the single most binary question in this campaign; the entry-risk note is
  how you refuse to leave it ambient.
- **Sanguine beat**: send today's end-of-day row with a 1-word mood tag that
  honestly names how writing R1 down felt. Owning the risk IS the Sanguine
  win — refusal to flinch.
- **Risk this day touches**: R1 (Imperial entry without relevant Master's)
  and R3 (Imperial statement GenAI rule).
- **Ship rule**: 80% at the 90-min cap on the entry-risk note — SHIP with
  one open question listed, do not inflate the note to look complete.

---

## 1. PhD research / applications — 90 min

**Workbook task:** Professor-first Day 2 — Read Imperial Computing PhD entry
guidance. Record the Bachelor's-only exception and the requirement that
Imperial statements be written by you without generative-AI help.
**Acceptance test:** entry-risk note saved → `evidence/2026-10-15/phd-entry-risk-note.md`.

The note must contain:
1. Imperial's exact wording on Bachelor's-only candidates ("not normally
   considered") — pasted verbatim with source URL and date-checked.
2. Imperial's exact wording on the GenAI statement rule — pasted verbatim,
   source URL, date-checked.
3. Your decision rule: *given this evidence, do I submit the December QRT
   application anyway*? Three bullets — reasons for yes, reasons for no, and
   the single data point that would flip the decision.
4. A date-boxed re-check on Imperial's guidance before the submission week
   (2026-11-25 per the workbook schedule).

- [ ] Imperial PhD guidance page opened and read in full
- [ ] Entry-risk note saved
- [ ] Risk Register R1 and R3 status lines updated with today's date

**Melancholic trap for today:** doom-looping on the Master's-gap question.
The rule is: write it down, log the decision gate, move on. The note's job
is to make the risk refuse-to-forget, not to resolve it today.

---

## 2. IELTS Academic — Listening — 60 min

**Workbook task:** Complete one timed section; replay only after scoring and
classify each miss: distractor, spelling, prediction, vocabulary or attention.
**Baseline day for Listening** — this is diagnostic.
**Acceptance test:** raw score / accuracy + 3 errors classified by taxonomy.

- [ ] One timed Listening section completed
- [ ] Score logged (no replay yet)
- [ ] Three errors classified using the rubric at
      `day-1-packet/02-ielts-reading-rubric.md` (same taxonomy applies to
      Listening — the five codes are shared).
- [ ] Only AFTER classification: replay missed segments; note the audio cue
      you missed.
- [ ] Row added to `evidence/2026-10-15/ielts.md`

**Melancholic trap:** blaming the audio speed. The rule for Listening is:
error cause is yours even when the speaker is fast. "Fast speaker" is not
on the taxonomy — pick one of the five codes.

---

## 3. System Design — 45 min

**Focus:** Payment API / idempotency.
**Workbook task:** Draw a payment endpoint with idempotency key, persisted
request state, timeout and safe retry; list duplicate-request failure modes.
**Acceptance test:** diagram + at least three named duplicate-request failure
modes.

Required beats:
1. Diagram showing: client → payment endpoint → idempotency store → ledger.
2. Idempotency key placement (header vs body; TTL; scope — per-user,
   per-merchant, global).
3. Timeout handling: client timeout vs server completion; the dangerous
   case of client timeout + server success.
4. Safe retry rules: retryable error classes vs non-retryable.
5. **At least three duplicate-request failure modes**: e.g., client retry
   after server succeeded but response lost; client retry with mutated body;
   two clients using the same key by accident.

Save to `evidence/2026-10-15/sd-idempotency.md`.

- [ ] Diagram
- [ ] Idempotency key policy
- [ ] Timeout handling discussion
- [ ] Safe-retry rules
- [ ] At least 3 duplicate-request failure modes
- [ ] 60-second spoken walkthrough (Sanguine beat)

---

## 4. DSA — Java 21 — 45 min

**Focus:** Hashing.
**Workbook task:** Solve Contains Duplicate and Valid Anagram. State expected
time/space complexity and test empty/single-item inputs.
**Acceptance test:** both solutions in Java 21 + complexity + edge-case tests.

Save to `evidence/2026-10-15/dsa-contains-duplicate.java` and
`dsa-valid-anagram.java`. Follow the pattern of Day 1's `04-dsa-two-sum.java`.

- [ ] Contains Duplicate: HashSet one-pass; O(n) time, O(n) space
- [ ] Valid Anagram: frequency array (26 chars) OR HashMap; O(n) time
- [ ] Edge cases per solution: empty string / single item / unicode (anagram)
- [ ] Weakest-pattern wall updated — hashing is the Day-1+2 pattern cluster;
      note whether speed-of-recall was faster or slower than Two Sum.

**Melancholic trap:** over-generalising to Unicode. For the acceptance test,
assume ASCII lowercase; note Unicode as a parking-lot item for Day 15.

---

## End-of-day row (5 min)

Append today's row to `performance-log.md` with:
- Evidence paths × 4 domains
- Confidence 1–5 × 4
- Mood tag (likely: *sobered* — R1 lands with weight)
- One strongest-pattern note
- One avoidance to name

## Parking lot

- (empty)
