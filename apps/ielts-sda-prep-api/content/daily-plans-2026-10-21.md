# Day 8 — Wednesday, 2026-10-21 — Week 2

*Source: Daily One-Look. First day of Week 2. The IELTS Reading rhythm
flips from pure diagnostic to error-pattern repair; PhD work shifts from
pipeline building to literature assurance.*

## The MELSAN read for today

- **Melancholic focus**: the literature-assurance paper is read AGAINST a
  specific question — "what does this paper *guarantee*?" Not "what does
  it say." Guarantees are formal; opinions are not.
- **Sanguine beat**: Week 2 is a new chapter. Sanguine voice treats
  chapter transitions as fresh energy — rename the mood tag this week to
  reflect the shift (last week's *scouting* / *sobered* becomes this
  week's *building*).
- **Risk this day touches**: R7 (research novelty too broad — reading one
  paper carefully is the start of the mitigation).
- **Ship rule**: *one* paper read deeply, not three skimmed. If the
  paper's abstract overpromises, pick a different one — do not finish a
  paper that is not teaching you.

---

## 1. PhD research / applications — 90 min

**Workbook task:** Literature: assurance — Read one paper on bounded
autonomy, runtime monitoring, shielding or formal verification; identify
what it guarantees.
**Acceptance test:** paper summary saved to `evidence/2026-10-21/phd-lit-01.md`
with:
1. Full citation (authors, year, venue, URL/DOI)
2. One-sentence problem the paper solves
3. **What the paper formally guarantees** — in the paper's own terms
4. What it does NOT guarantee (negative scope — the authors' honesty)
5. What this guarantee implies for Payflow's current verifier (does our
   verifier claim this guarantee? If yes, under what assumptions? If no,
   is it the next upgrade?)
6. One citation this paper makes that is worth tracking for Day 15
   (literature matrix day)

Candidate reading list (pick one; verify via Google Scholar / arXiv):
- Belardinelli et al. on shielding (connects to Priority 8 supervisor)
- Alshiekh et al., "Safe Reinforcement Learning via Shielding" (2018)
- Lu et al. on runtime verification for ML systems
- Any Toni paper on argumentation-based abstention (connects to Priority 4)
- Katz et al., "Reluplex: An Efficient SMT Solver for Verifying DNN"
  (classic formal-verification entry point)

- [ ] One paper read in full (sections glanced only where safe)
- [ ] Six-row summary saved
- [ ] If reading a Belardinelli or Toni paper, append a one-paragraph
      update to the matching supervisor card ("read X, found Y worth
      asking about")

**Melancholic trap:** sliding into "paper two is also relevant, I'll
start that too." No. Finish one. The second paper is Day 9.

---

## 2. IELTS Academic — Reading — 60 min

**Workbook task:** Complete one timed passage; log raw correct answers,
question types missed, and evidence/paraphrase for each wrong answer.
**Focus on paraphrase, structure and error classification** (Week 2
sharpening of the Week 1 baseline).
**Acceptance test:** raw score + 3 errors classified + explicit comparison
to Day 1 Reading baseline.

- [ ] Timed passage completed
- [ ] Score logged
- [ ] Three errors classified with the five-code taxonomy
- [ ] **Comparison beat** (new in Week 2): one sentence per error naming
      whether this error type also appeared on Day 1. If yes, the pattern
      is recurring and goes on the top-3-errors list for the week.
- [ ] Saved to `evidence/2026-10-21/ielts.md`

---

## 3. System Design — 45 min

**Focus:** Delivery guarantees.
**Workbook task:** Compare at-most-once, at-least-once and effectively-once
outcomes; design an idempotent consumer.
**Acceptance test:** comparison table + idempotent-consumer design.

- [ ] Comparison table: for each guarantee, (what breaks? at-most-once ⇒
      message loss; at-least-once ⇒ duplicates; effectively-once ⇒ complex
      coordination)
- [ ] Idempotent consumer design: consumer tracks processed message IDs,
      checks on arrival, no-ops on duplicate
- [ ] Where IDs live (local store? external DB? expiry policy?)
- [ ] Failure mode: consumer crashes after processing but before marking
      done → duplicate on recovery → idempotency saves it
- [ ] Saved to `evidence/2026-10-21/sd-delivery-guarantees.md`

---

## 4. DSA — Java 21 — 45 min

**Focus:** Binary search.
**Workbook task:** Solve Search Insert Position. Explain lower-bound
semantics.
**Acceptance test:** iterative solution + written lower-bound invariant.

- [ ] Iterative binary search variant returning the first index where
      nums[i] >= target
- [ ] Written invariant: "lo is the smallest index known to be a valid
      insert position; hi is one past the largest such index"
- [ ] Edge: target smaller than all elements (return 0)
- [ ] Edge: target larger than all elements (return length)
- [ ] Edge: target equal to an existing element (return that index)
- [ ] Saved to `evidence/2026-10-21/dsa-search-insert.java`

**Weakest-pattern wall:** binary search is the Day 7+8 pair. If recall
was slower than Day 7, the pattern needs one more rep in Week 2 — add
a parking-lot item.

---

## End-of-day row + parking lot — standard shape.
