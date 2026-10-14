# Performance log — 49 days, one row per evening

*Mirror of the workbook Performance Log sheet in Markdown. Fill the end-of-day
row in 5 minutes. Each row is a MELSAN artefact: evidence (Melancholic) +
confidence + streak (Sanguine).*

## Row shape

```
### 2026-MM-DD — Day N — <mood tag in one word>

| Domain | Status | Evidence file | Confidence 1–5 | Note |
|---|---|---|---|---|
| PhD research | ✅/⚠️/❌ | `evidence/.../phd-*.md` | X | one line |
| IELTS | ✅/⚠️/❌ | `evidence/.../ielts.md` | X | one line + taxonomy totals |
| System Design | ✅/⚠️/❌ | `evidence/.../sd.md` | X | one line |
| DSA | ✅/⚠️/❌ | `evidence/.../dsa.*` | X | pattern + whether re-solvable |

**Streak**: N consecutive days ✅ across all four domains
**One strongest-pattern note**: <single sentence>
**One avoidance to name**: <what did I dodge today, and why?>
**Sanguine beat of the day**: <human touchpoint sent OR momentum signal visible>
**Parking lot additions**: <ideas to review Sunday, do NOT act on>
```

**Status legend**: ✅ acceptance test met (evidence saved); ⚠️ 80% rule
invoked (shipped with a logged gap); ❌ not completed (triggers Sunday
recovery note).

## The entries

### 2026-10-14 — Day 1 — <fill at end of day>

| Domain | Status | Evidence file | Confidence 1–5 | Note |
|---|---|---|---|---|
| PhD research |   | `day-1-packet/01-phd-qrt-fit-note.md` |   | 4-row fit note; rank at end |
| IELTS |   | `evidence/2026-10-14/ielts.md` |   | baseline Reading diagnostic |
| System Design |   | `evidence/2026-10-14/sd.md` |   | CAP one-pager |
| DSA |   | `evidence/2026-10-14/dsa.java` |   | Two Sum, brute + HashMap |

**Streak**: 0 → 1 if all four ship today
**One strongest-pattern note**: 
**One avoidance to name**: 
**Sanguine beat of the day**: *target* — York eligibility email sent
**Parking lot additions**: 

---

(Day 2 onwards: duplicate the row shape and add as you go. The last entry
should be 2026-12-01, Day 49.)

## End-of-week aggregator

Every Sunday, after filling the weekly entry, append a two-line summary:

```
Week N (dates):
  Completion: X / 28 acceptance tests met (W%)
  Streak: N consecutive days all-four-✅
  Highest-confidence domain: <domain> (avg C)
  Lowest-confidence domain: <domain> (avg C) — recovery plan: <specific>
```
