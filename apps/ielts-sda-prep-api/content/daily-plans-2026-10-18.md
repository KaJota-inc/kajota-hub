# Day 5 — Sunday, 2026-10-18 — Week 1

*Source: Daily One-Look. Day 5 is OUTREACH day — individualised drafts to
Demetriou and Wang. Also Sunday — Weekly Scorecard runs at the end of today.*

## The MELSAN read for today

- **Melancholic focus**: *individualised* means specific-paper, specific-
  project, specific-question. The Risk Register explicitly bans generic
  copy-paste. Two drafts, two genuinely different openings, two different
  one-paragraph bodies.
- **Sanguine beat**: Sunday Weekly Scorecard — the first one. Three wins,
  one celebration, one person to thank. Week-1 completion is itself a
  celebration beat; honour it.
- **Risk this day touches**: R3 (GenAI statement rule — these are OUTREACH
  emails, which are permitted, but the discipline of individualised writing
  is the same muscle you need for the statement) and R7 (novelty — the
  drafts are the first external test of whether your fit maps are
  defensible to a human reader).
- **Ship rule**: two drafts at the 90-min cap. If one lags, finish the
  Demetriou draft (higher priority) and parking-lot the Wang draft to Day 6.

---

## 1. PhD research / applications — 90 min

**Workbook task:** Professor-first Day 5 — Prepare individual outreach to
Demetriou and Song Wang using your own wording. Do not send a generic
copy-paste pitch.
**Acceptance test:** two tailored drafts and source links saved.

Create two files:
- `outreach-drafts/demetriou.md`
- `outreach-drafts/wang.md`

Each draft must:
1. Reference a specific project (SD-2 for Demetriou; "your work on
   reliability testing for autonomous agents" with a specific paper for
   Wang).
2. State the fit hypothesis in your own one paragraph (not lifted from
   the supervisor card).
3. Ask one precise question — not a generic "would you consider
   supervising."
4. State the primary logistical reality: Fall 2027 start, QRT round 1 Dec
   2026 (Demetriou) OR direct-entry eligibility pending EECS admin reply
   (Wang).
5. Offer three calendar windows OR ask them to propose one.

- [ ] Demetriou draft complete
- [ ] Wang draft complete
- [ ] Each draft reviewed for "would this read as a template to the
      recipient?" — if yes, rewrite the specific sentence that triggered it
- [ ] Status timelines in `supervisors/demetriou.md` and `song-wang.md`
      updated with "Ready to contact" and today's date

**Melancholic trap:** polishing the Demetriou draft for 60 min and
leaving Wang unwritten. 30-minute budget per draft, hard. The Sunday
scorecard will catch the overrun if you let it.

---

## 2. IELTS Academic — Repair & review — 60 min

**Workbook task:** Repeat a short task in the weakest skill; correct 3
recurring errors and add 5 useful collocations to the log.
**Acceptance test:** short task done + 3 error patterns corrected + 5
collocations logged.

Choose the weakest skill from Week-1 Performance Log:
- Lowest average confidence across Days 1-4 → that's the skill today

- [ ] Short task completed in the weakest skill
- [ ] Three recurring errors from the week identified
- [ ] For each, a specific correction (not "be more careful")
- [ ] Five academic collocations added to vocabulary log
- [ ] Saved to `evidence/2026-10-18/ielts-repair.md`

---

## 3. System Design — 45 min

**Focus:** Rate limiting.
**Workbook task:** Design a token-bucket rate limiter; discuss per-user vs
per-client limits and distributed state.
**Acceptance test:** diagram + per-user vs per-client comparison + distributed-
state solution.

Required beats:
1. Token-bucket algorithm: bucket size, refill rate, request cost
2. Per-user limit: scope and failure mode (one user drowns the API)
3. Per-client limit: scope and failure mode (multi-tenant client fairness)
4. Distributed state: where is the counter? (Redis + atomic decrement;
   discuss the race, discuss the fallback when Redis is down)

- [ ] Diagram
- [ ] Per-user vs per-client table
- [ ] Distributed-state solution
- [ ] Saved to `evidence/2026-10-18/sd-rate-limiter.md`

---

## 4. DSA — Java 21 — 45 min

**Focus:** Sliding window.
**Workbook task:** Solve Longest Substring Without Repeating Characters.
State when the left pointer moves.
**Acceptance test:** sliding-window with HashMap of last-seen indices;
written invariant on when `left` advances.

- [ ] Solution with `left`/`right` pointers + HashMap<Character, Integer>
- [ ] Written invariant: "window s[left..right] contains no duplicates;
      when s[right] is already in the map at index p ≥ left, left jumps to
      p + 1"
- [ ] Edge cases: empty, single char, all-same, all-distinct
- [ ] Saved to `evidence/2026-10-18/dsa-longest-substring.java`

---

## End-of-day row — standard shape.

## 📅 Sunday Weekly Scorecard — RUN THIS

Open `weekly-review-template.md` and work through all 10 steps.

Week-1 exit gate from the workbook: *"Baseline saved; eligibility/funding
risks explicitly logged."* Confirm:
- [ ] Day 1 IELTS Reading baseline saved
- [ ] Day 2 IELTS Listening baseline saved
- [ ] Day 1 entry-risk note on Imperial Bachelor's rule saved
- [ ] Day 2 Imperial entry-risk note saved
- [ ] York direct-entry eligibility email sent (Day 1)
- [ ] Risk Register R1, R2, R3 statuses current
- [ ] Three wins named
- [ ] One celebration named + delivered
- [ ] One person to thank — note sent
- [ ] Parking lot drained
- [ ] One stop / one start / one keep decided for Week 2

**The first Sunday matters more than any other.** The campaign's four-domain
rhythm either locks in this week or you repeat the kick-off next Monday.
