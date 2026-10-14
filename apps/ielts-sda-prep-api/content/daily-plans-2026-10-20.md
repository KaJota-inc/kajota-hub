# Day 7 — Tuesday, 2026-10-20 — Week 1

*Source: Daily One-Look. Day 7 closes Week 1: outreach-order decision,
HF-1 vs SD-2 call, Week-1 integration.*

## The MELSAN read for today

- **Melancholic focus**: a *decision*, not a review. Top-3 ranked leads
  with follow-up dates AND an explicit go/hold per lead. "I'll think about
  it" is not an answer today.
- **Sanguine beat**: outreach decisions mean follow-ups are now LOCKED
  into the calendar — human-shaped artefacts land in your calendar for the
  next three weeks. The Sanguine voice loves scheduled touchpoints.
- **Risk this day touches**: R4 (QRT project slot — HF-1 vs SD-2 rank
  settled today), R1 (Imperial entry — the final go/hold incorporates the
  entry risk).
- **Ship rule**: three ranked leads with dated next actions by the 90-min
  cap. A ranking of two with one "defer to Day 10" is better than four
  with no commitment.

---

## 1. PhD research / applications — 90 min

**Workbook task:** Professor-first Day 7 — Decide outreach order and next
steps based on research fit, vacancy signal, and admission feasibility.
**Acceptance test:** top 3 ranked leads, follow-up dates, and explicit
go/hold decision for each, saved to
`evidence/2026-10-20/phd-outreach-ranking.md`.

Required format:

| Rank | Lead | Primitive | Follow-up date | Go/Hold | Reason |
|---|---|---|---|---|---|
| 1 | *{supervisor}* | *{primitive hit}* | *{YYYY-MM-DD}* | GO | *{why}* |
| 2 | *{supervisor}* | *{primitive hit}* | *{YYYY-MM-DD}* | GO | *{why}* |
| 3 | *{supervisor}* | *{primitive hit}* | *{YYYY-MM-DD}* | *{GO/HOLD}* | *{why}* |

Also:
- Explicit **HOLD** rows for the 5 remaining shortlisted supervisors with
  the trigger that would promote them.
- Explicit **ARCHIVE** rows for any supervisor you have decided against.

- [ ] Ranking saved
- [ ] Follow-up dates added to each supervisor card's Status Timeline
- [ ] If HF-1 (Fan) decision is "list as secondary QRT reference", add
      that to `supervisors/hongxiang-fan.md`

**Melancholic trap:** adding a fourth and fifth rank "in case." The
discipline is top-3 only. Everything else is HOLD with a trigger.

---

## 2. IELTS Academic — Writing Task 2 — 60 min

**Workbook task:** Write one 40-minute essay (at least 250 words); use 20
minutes to audit task response, paragraph progression, grammar and
vocabulary.
**Acceptance test:** full essay + 20-min audit.

Reliable 7+ structure for Task 2:
1. Introduction — paraphrase + clear position (2 sentences)
2. Body 1 — one position with support (reason + example + counter-caveat)
3. Body 2 — second position OR deepened support
4. Conclusion — restated position + one implication

Audit:
- **Task response**: fully addressed? Position clear?
- **Coherence/cohesion**: paragraph progression logical?
- **Lexical resource**: 3+ precise academic verbs/collocations?
- **Grammar range**: at least two conditional / passive / relative-clause
  structures?

- [ ] Essay in 40 min
- [ ] Audit in 20 min
- [ ] Saved to `evidence/2026-10-20/ielts-wt2.md`

---

## 3. System Design — 45 min

**Focus:** Kafka basics.
**Workbook task:** Draw producer → topic/partition → consumer group;
explain ordering scope, key choice and scaling.
**Acceptance test:** diagram + ordering-scope rule + key-choice reasoning.

- [ ] Diagram: producer → topic → partitions → consumer group members
- [ ] Ordering scope: ordered within partition, not across
- [ ] Key choice: same key → same partition → preserved order per key
- [ ] Scaling: number of consumers ≤ number of partitions (one consumer
      per partition in a group)
- [ ] Common anti-pattern: hashing on a low-cardinality key → hot partition
- [ ] Saved to `evidence/2026-10-20/sd-kafka.md`

---

## 4. DSA — Java 21 — 45 min

**Focus:** Binary search.
**Workbook task:** Implement Binary Search; test empty array, one item,
absent key and boundary indices.
**Acceptance test:** iterative binary search + all four edge cases.

- [ ] Iterative binary search returning index of target or -1
- [ ] Loop invariant stated in comment: "if target exists in `nums`, its
      index is in `[lo, hi]`"
- [ ] Edge: empty array (return -1)
- [ ] Edge: single element present (return 0) and absent (return -1)
- [ ] Edge: target at index 0 and target at index length-1
- [ ] Bonus: lower-bound variant (first index where nums[i] >= target)
- [ ] Saved to `evidence/2026-10-20/dsa-binary-search.java`

**Melancholic trap:** off-by-one on the `hi` bound. Pick one convention
(`hi = n-1` inclusive OR `hi = n` exclusive) and keep it consistent.

---

## End-of-day row + parking lot — standard shape.

## Week-1 preparation note

Tomorrow (Day 8, Wednesday 2026-10-21) opens Week 2 — Reading again,
first literature-assurance paper (bounded autonomy / runtime monitoring).
Make sure tonight's end-of-day row flags any Week-1 shortfall so Monday's
Weekly Scorecard correction landed.
