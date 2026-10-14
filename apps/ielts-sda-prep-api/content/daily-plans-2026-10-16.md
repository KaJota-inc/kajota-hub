# Day 3 — Friday, 2026-10-16 — Week 1

*Source: Daily One-Look. Day 3 is Song Wang day — the York direct-entry
eligibility ask doubles as a Sanguine win if you time it right.*

## The MELSAN read for today

- **Melancholic focus**: a precisely-cited 5-bullet fit map for Song Wang.
  Each bullet names a specific paper or project page section + which thesis
  primitive it hits + why.
- **Sanguine beat**: today's Daily One-Look explicitly says *"In parallel,
  send York the direct-entry degree-classification question."* You already
  sent `outreach-drafts/00-york-eligibility-email.md` on Day 1. Log that
  send in today's PhD acceptance row and claim the Sanguine win — the
  parallel task is already discharged.
- **Risk this day touches**: R2 (York direct-entry subject fit) and R8
  (research novelty too broad — Wang's reliability framing sharpens the
  novelty question).
- **Ship rule**: five bullets at the 90-min cap. Four with evidence beats
  five with vibes.

---

## 1. PhD research / applications — 90 min

**Workbook task:** Professor-first Day 3 — Review Song Wang's official
profile and 2 relevant papers; draft a 5-bullet fit map. In parallel, send
York the direct-entry degree-classification question.
**Acceptance test:** evidence-based fit map + email sent/logged.

- [ ] Song Wang's official profile re-read: https://www.eecs.yorku.ca/~wangsong/
- [ ] Two recent reliability/agent papers from his page read
- [ ] 5-bullet fit map appended to `supervisors/song-wang.md` under the
      "Thesis-fit hypothesis" section (replace the current scaffold)
- [ ] Each bullet cites a specific paper / section
- [ ] Log York admin email send (already sent Day 1) in today's PhD row

**Melancholic trap:** paper-reading rabbit holes. If a paper's abstract
does not clearly connect to one of the three thesis primitives in the
first 10 min, close it and pick the next. The acceptance test is five
cited bullets, not deep reading of two long papers.

---

## 2. IELTS Academic — Writing Task 1 — 60 min

**Workbook task:** Write a 20-minute Academic Task 1 response (at least
150 words); audit overview, comparisons, data accuracy and grammar.
**Acceptance test:** full essay + 20-min audit against the four criteria.

Structure that reliably hits 7+:
1. Paraphrase of the prompt (1 sentence)
2. Overview — two biggest trends/comparisons, no numbers (2 sentences)
3. Body paragraph 1 — group of data points, with figures
4. Body paragraph 2 — other group, with figures and comparisons

Audit against:
- **Task response**: all key features covered?
- **Coherence/cohesion**: paragraphing clean, linkers varied?
- **Lexical resource**: at least three precise academic verbs/collocations?
- **Grammar range**: at least two complex sentence structures?

- [ ] Essay written in 20 min (timer on)
- [ ] 20-min audit against the four criteria
- [ ] Self-estimated band + three strongest / three weakest moves
- [ ] Saved to `evidence/2026-10-16/ielts-wt1.md`

**Melancholic trap:** rewriting mid-timer. The timer is sacred — audit
AFTER, not during.

---

## 3. System Design — 45 min

**Focus:** REST and API gateway.
**Workbook task:** Draw client → gateway → services; annotate authentication,
rate limits, timeout, versioning and service ownership.
**Acceptance test:** diagram with all five annotations.

- [ ] Diagram: client → API gateway → N backend services
- [ ] Authentication annotation (where tokens are validated)
- [ ] Rate-limit annotation (where enforced, per-key vs per-IP)
- [ ] Timeout annotation (gateway timeout < sum of service timeouts)
- [ ] Versioning annotation (URL path vs header, breaking vs non-breaking)
- [ ] Service-ownership annotation (which team owns which path prefix)
- [ ] Saved to `evidence/2026-10-16/sd-rest-gateway.md`
- [ ] 60-sec spoken walkthrough

---

## 4. DSA — Java 21 — 45 min

**Focus:** Array scan.
**Workbook task:** Solve Best Time to Buy and Sell Stock. Explain the
running minimum invariant.
**Acceptance test:** O(n) solution + written invariant + edge-case tests.

- [ ] One-pass solution with `minSoFar` + `bestProfit`
- [ ] Written invariant: "at index i, `minSoFar` is the min of prices[0..i-1]
      so `prices[i] - minSoFar` is the best possible sell on day i"
- [ ] Edge cases: empty, single day, monotonically decreasing (profit = 0)
- [ ] Saved to `evidence/2026-10-16/dsa-stock.java`
- [ ] Weakest-pattern wall updated

**Melancholic trap:** reaching for Kadane's variant when the acceptance
test is one-pass max-profit. Note Kadane as a Day-28 (DP) parking-lot item.

---

## End-of-day row + parking lot — standard shape (see `daily/_template.md`).
