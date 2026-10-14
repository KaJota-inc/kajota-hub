# phd-prep — Imperial × York, 14 Oct – 1 Dec 2026

Companion workspace for `~/Downloads/Imperial_York_Premium_PhD_Prep_Plan.xlsx`.
The workbook is the source of truth for *what* each day requires. This folder
is the implementation grammar — MELSAN-shaped scaffolding for *how* each day
gets done and the evidence captured.

## Shape

```
MELSAN.md                     # the operating grammar; read first
daily/
  _template.md                # one file per day; copy to <date>.md
  2026-10-14.md               # Day 1 (today) pre-filled
  2026-10-15.md               # Day 2 pre-filled
  …
day-1-packet/
  01-phd-qrt-fit-note.md      # 4-row fit note (SD-1, SD-2, HF-1, FB-1)
  02-ielts-reading-rubric.md  # taxonomy + log template
  03-system-design-cap.md     # distributed-systems one-pager scaffold
  04-dsa-two-sum.java         # two solutions + edge tests + complexity
supervisors/
  _template.md
  demetriou.md                # Priority 1 — Imperial QRT SD-2
  song-wang.md                # Priority 2 — York EECS
  casale.md                   # Priority 3 — Imperial Systems
  …
outreach-drafts/
  00-york-eligibility-email.md   # critical Day-1 unblock
  wang.md                        # York direct-entry fit question
  demetriou.md                   # SD-2 after Day 5
risk-register.md              # live copy of workbook risks
performance-log.md            # mirror of workbook Performance Log
weekly-review-template.md     # Sunday checkpoint
```

## Daily rhythm (per MELSAN grammar)

| Time | Domain | Minutes | Melancholic form | Sanguine form |
|---|---|---|---|---|
| Morning | PhD research | 90 | Acceptance test with evidence saved | Status chip flip + streak +1 |
| Morning | IELTS | 60 | One task, corrected, error-taxonomy-logged | Confidence 1–5 recorded |
| Afternoon | System Design | 45 | One diagram + one explicit trade-off | Spoken 60-sec walkthrough to self |
| Afternoon | DSA (Java 21) | 45 | Code tested + complexity + pattern logged | Weakest-pattern wall updated |

End of day (5 min): fill `performance-log.md` row — evidence file paths,
confidence 1-5, one strongest-pattern note, one avoidance to name.

Sunday (30 min): `weekly-review-template.md` — blockers, three wins, one
celebration, one person to thank, parking-lot drained into next week's plan.

## Hard rules

1. **No GenAI help on Imperial statements.** This folder plans, checklists,
   drafts outreach, builds DSA/SD content, and tracks evidence. The personal
   statement and research statement are written by the applicant alone.
2. **The ship rule.** 80% at the time-cap → ship + log the gap. Perfection
   loses the Sunday scorecard.
3. **Parking lot first, pivots never.** New ideas → `weekly-review-template.md`
   parking lot; acted on only after Sunday review.

## Where to start today (2026-10-14, Day 1)

1. Read `MELSAN.md` once.
2. Open `daily/2026-10-14.md` — it is pre-filled from the Daily One-Look.
3. Work the four domains in order. Save evidence files under `evidence/<date>/`.
4. End-of-day: fill today's row in `performance-log.md`.
5. **Day-1 critical unblock**: send `outreach-drafts/00-york-eligibility-email.md`
   today. This question gates the entire York track and the Risk Register
   flags it as HIGH / CRITICAL — do not sleep on it.
