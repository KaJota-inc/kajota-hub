# Daily Domain Workflows — the four blocks, run the MELSAN way

*240 minutes, four domains, every day 14 Oct–1 Dec. Each SOP below is the MELSAN loop specialised
to a domain, carrying that day's acceptance test straight from the workbook's Daily One-Look sheet.
Clock times are examples (from the Daily Routine sheet) — keep the duration and the output, move the
blocks around CTO duties and prayer.*

The daily non-negotiable, from the workbook: **the milestone is the smallest meaningful output, not
time spent.** Four acceptance tests pass, or the day is amber.

**Each block is one run of MELSAN-Execute**, bracketed by **MELSAN-Launch** in the morning and
**MELSAN-Close** in the evening (see `00-melsan-operating-system.md`). Save every artefact to
`day-packs/<date>/` as you go, then mirror the status into the workbook — don't leave the write-up
for later.

---

## Block 1 · PhD research / applications — 90 min *(Critical)*

The heavyweight block. **Melancholic leads the research; Sanguine leads the outreach.** Which one is
front depends on the day's task type in Daily One-Look (discovery/literature/methodology vs
outreach/statements/QA).

1. **[MEL] Measure.** Copy today's PhD acceptance test verbatim. Research days end in a *saved
   artefact* (fit-note, literature matrix, hypothesis set, methodology draft); application days end
   in a *logged action* (email sent, QA checklist cleared, route decision recorded).
2. **[SAN] Engage.** One spoken sentence: "Today I'm producing X, which strengthens the thesis
   by Y." Energy on; thesis in view.
3. **[MEL] Labour — 50 min.** Read/write deep. For literature: separate *established fact · my
   hypothesis · proposed contribution · open question* (the workbook's four-column discipline). For
   methodology: workloads, policies, metrics, failure injection, ablation, reproducibility.
4. **[MEL] Scrutinise — source-verify.** Every factual claim → checked against the Verified Sources
   sheet or the official page. Every novelty claim → closest prior work named and the difference
   stated. No unsupported "this is novel."
5. **[SAN] Articulate.** Two-minute spoken defence of today's artefact: what it is, why it matters,
   what would disprove it. Record it — this is viva rep #1.
6. **[MEL+SAN] Next + evidence.** One dated next action; file proof in Performance Log (PhD
   deliverable column).

**Statement days — the gate fires here.** When the task is the personal/research statement:
Melancholic builds the *skeleton* (section list, evidence inventory, requirement checklist: 1–2 pp
personal, 3–4 pp research, ≥2 references) and later runs an *adversarial critique* ("does every
section answer a research question? cut generic AI background"). **You write every sentence of prose
yourself** — the Sanguine voice from your daily Articulate reps is the drafting instrument. No
generated statement text, ever. That is the Imperial rule and it is also your viva insurance.

---

## Block 2 · IELTS Academic — 60 min *(Daily)*

**Sanguine-forward** (expression, fluency, warmth) **with Melancholic error-taxonomy discipline.**
Skill rotates by day per Daily One-Look: Reading · Listening · Writing T1 · Mini-mock · Repair ·
Speaking · Writing T2.

1. **[MEL] Measure.** Today's skill + its acceptance test. Writing tasks use real timing (T1 ≥150
   words ~20 min; T2 ≥250 words ~40 min, weighted double). Speaking uses the four official criteria:
   fluency/coherence, lexical resource, grammatical range/accuracy, pronunciation.
2. **[SAN] Engage — 5 min.** Review yesterday's three logged errors aloud; warm the voice.
3. **[MEL] Labour — 40 min.** Do the task under exam timing. No stopping to fix mid-task.
4. **[MEL] Scrutinise — 15 min.** Score it. Classify every miss into a taxonomy (Reading/Listening:
   distractor · spelling · prediction · vocabulary · attention; Writing: task response · progression
   · grammar · lexis). Record **3 highest-impact corrections** and **5 collocations** into the log.
5. **[SAN] Articulate.** For speaking days, this *is* the task. For writing/reading days, say your
   three corrections out loud as rules ("I will signpost the overview sentence first"). Expression
   compounds across the week.
6. **[MEL+SAN] Next + evidence.** Log raw score/accuracy + the three corrections in Performance Log.
   Target: beat the Week-1 baseline on your weakest criterion by a measurable margin.

*Reality check from the workbook: self-scored bands are estimates, not official scores. 8.0/7.5 is a
personal stretch target; York's floor is IELTS 7. Train high; don't mistake the practice band for a
result.*

---

## Block 3 · System Design — 45 min *(Daily)*

**Melancholic structure; Sanguine plain-language explanation.** The day's topic tracks the thesis
spine — distributed foundations → payment/idempotency → Kafka/outbox/ledger → observability →
inference/routing → bounded autonomy/verification → control-plane defence.

1. **[MEL] Measure — recall 10 min.** State today's focus and the acceptance test (a diagram or a
   structured explanation with assumptions and failure cases).
2. **[SAN] Engage.** One sentence on where today's component sits in the risk-adaptive inference
   thesis.
3. **[MEL] Labour — 20 min.** Draw it. Data path, trust boundaries, idempotency keys, state
   transitions. One explicit trade-off.
4. **[MEL] Scrutinise — 10 min.** Mark every single point of failure, the fallback, and the safe-stop
   condition. For finance topics: check the deterministic invariants (authorization, idempotency,
   ledger consistency, delegated authority) cannot be bypassed.
5. **[SAN] Articulate — 5 min.** Five-minute spoken walkthrough: what it does, what fails, how it
   recovers, how you'd measure correctness. This is simultaneously your design-interview rep and a
   viva rep.
6. **[MEL+SAN] Next + evidence.** File the diagram/notes (System Design artifact column).

> The thesis payoff: by Week 6 these daily diagrams compose into one control-plane design you can
> defend in five minutes — the workbook's Week-6 exit gate.

---

## Block 4 · DSA — Java 21 — 45 min *(Daily)*

**Melancholic correctness and complexity; Sanguine spoken explanation.** Pattern tracks the workbook:
arrays/hashing → sliding window → binary search → linked list → stack/queue → trees → graphs → DP →
intervals → design (LRU/Trie) → timed mocks.

1. **[MEL] Measure — recall 5 min.** Name today's problem(s) and the acceptance test (tested + pattern
   & complexity logged; specific edge cases named).
2. **[SAN] Engage.** State the pattern and why it fits, out loud, before coding.
3. **[MEL] Labour — 25 min.** Clarify → brute force → optimise → code in Java 21 → test. Name the
   invariant (running minimum, left-pointer rule, lower-bound semantics, stack contents…).
4. **[MEL] Scrutinise — 10 min.** Edge cases from the workbook (empty, single item, duplicates,
   absent key, boundaries). State time/space complexity and justify it.
5. **[SAN] Articulate — 5 min.** Explain correctness and complexity aloud in three minutes — the
   workbook's recurring "explain, don't just code" rep, and a fluency rep too.
6. **[MEL+SAN] Next + evidence.** Log code/tests + tag any error as concept · implementation ·
   complexity · edge case · time-management. The error log is what Week-5/6/7 review days consume.

*Honesty gate: completing a problem is not mastering it. Mastery = re-solving from a blank editor,
explaining it aloud. The Melancholic logs the difference; the Sanguine doesn't let you pretend.*

---

## End-of-day 3-minute close (both temperaments)

- **[MEL]** Four acceptance tests: pass / partial / miss? Mark Daily One-Look statuses honestly.
- **[SAN]** One sentence of credit for what landed today — morale is a 49-day resource, spend it.
- **[MEL+SAN]** Confirm tomorrow's four acceptance tests are understood before you close the laptop.
